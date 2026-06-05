import re
import requests
from typing import Dict, List, Any

# Emergency thresholds
EMERGENCY_KEYWORDS = [
    "chest pain", "severe chest pain", "shortness of breath", "difficulty breathing",
    "unconscious", "fainting", "severe bleeding", "heavy bleeding",
    "stroke", "slurred speech", "sudden weakness", "sudden numbness",
    "severe allergic reaction", "anaphylaxis", "not breathing", "broken bone", "fracture",
    "heart attack", "cardiac arrest"
]

EMERGENCY_CONTACTS = {
    "india": {
        "police": "112",
        "ambulance": "108",
        "note": "112 is pan-India emergency. 108 is a common ambulance number in many states."
    },
    "global": {
        "police": "112",
        "ambulance": "112",
        "note": "Use your local emergency number if different."
    },
    "us_uk": {
        "police": "911 / 999",
        "ambulance": "911 / 999",
        "note": "911 (US), 999 or 112 (UK)."
    },
}

COMMON_DRUGS = [
    "aspirin", "ibuprofen", "paracetamol", "acetaminophen", "metformin", "lisinopril",
    "amoxicillin", "atorvastatin", "albuterol", "omeprazole", "gabapentin", "sildenafil"
]

COMMON_SYMPTOMS = {
    "fever": "Fever",
    "cough": "Cough",
    "headache": "Headache",
    "migraine": "Migraine",
    "diabetes": "Diabetes Mellitus",
    "asthma": "Asthma",
    "hypertension": "Hypertension",
    "arthritis": "Arthritis",
    "insomnia": "Sleep Initiation and Maintenance Disorders",
    "anxiety": "Anxiety Disorders",
    "depression": "Depressive Disorder",
    "nausea": "Nausea",
    "diarrhea": "Diarrhea",
    "allergy": "Hypersensitivity"
}

class SymptomAnalyzer:
    def __init__(self):
        pass

    def check_emergency(self, text: str) -> Dict[str, Any]:
        lower_text = text.lower()
        for kw in EMERGENCY_KEYWORDS:
            if kw in lower_text:
                return {"is_emergency": True, "trigger": kw}
        return {"is_emergency": False, "trigger": None}

    def detect_drugs(self, text: str) -> List[str]:
        lower_text = text.lower()
        detected = []
        for drug in COMMON_DRUGS:
            if re.search(r'\b' + re.escape(drug) + r'\b', lower_text):
                detected.append(drug)
        return detected

    def detect_symptoms(self, text: str) -> List[str]:
        lower_text = text.lower()
        detected = []
        for kw, cond in COMMON_SYMPTOMS.items():
            if re.search(r'\b' + re.escape(kw) + r'\b', lower_text):
                detected.append(cond)
        return detected

    def query_clinical_trials(self, condition: str) -> List[Dict[str, Any]]:
        """
        Query ClinicalTrials.gov API v2 for active trials matching the condition.
        """
        url = "https://clinicaltrials.gov/api/v2/studies"
        params = {
            "query.cond": condition,
            "filter.overallStatus": "RECRUITING",
            "pageSize": 3
        }
        trials = []
        try:
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                for study in data.get("studies", []):
                    protocol = study.get("protocolSection", {})
                    ident = protocol.get("identificationModule", {})
                    status_mod = protocol.get("statusModule", {})
                    sponsor_mod = protocol.get("sponsorCollaboratorsModule", {})

                    trials.append({
                        "nct_id": ident.get("nctId", "N/A"),
                        "title": ident.get("briefTitle", ident.get("officialTitle", "Untitled Study")),
                        "status": status_mod.get("overallStatus", "UNKNOWN"),
                        "sponsor": sponsor_mod.get("leadSponsor", {}).get("name", "Unknown Sponsor"),
                        "link": f"https://clinicaltrials.gov/study/{ident.get('nctId')}" if ident.get("nctId") else "#"
                    })
        except Exception as e:
            print(f"[Analyzer] ClinicalTrials API error: {e}")
        return trials

    def query_openfda_drug(self, drug_name: str) -> Dict[str, Any]:
        """
        Query OpenFDA drug label API for warnings and usage details.
        """
        url = "https://api.fda.gov/drug/label.json"
        params = {
            "search": f"openfda.brand_name:{drug_name} OR openfda.generic_name:{drug_name}",
            "limit": 1
        }
        try:
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    result = results[0]
                    return {
                        "name": drug_name.capitalize(),
                        "brand_name": result.get("openfda", {}).get("brand_name", [drug_name.capitalize()])[0],
                        "generic_name": result.get("openfda", {}).get("generic_name", [drug_name.capitalize()])[0],
                        "purpose": result.get("purpose", ["Information not available"])[0][:200] + "...",
                        "indications_and_usage": result.get("indications_and_usage", ["Information not available"])[0][:300] + "...",
                        "warnings": result.get("warnings", ["Information not available"])[0][:300] + "..."
                    }
        except Exception as e:
            print(f"[Analyzer] OpenFDA API error: {e}")
        return {}

    def analyze_query(self, text: str) -> Dict[str, Any]:
        emergency_info = self.check_emergency(text)
        detected_drugs = self.detect_drugs(text)
        detected_conditions = self.detect_symptoms(text)

        # Query ClinicalTrials for first matched condition
        trials = []
        if detected_conditions:
            trials = self.query_clinical_trials(detected_conditions[0])
        elif not emergency_info["is_emergency"]:
            # Fallback search if no explicit match but not emergency
            words = [w for w in re.findall(r'\b\w{4,}\b', text.lower()) if w not in COMMON_DRUGS]
            if words:
                trials = self.query_clinical_trials(words[0])

        # Query OpenFDA for first matched drug
        drug_facts = {}
        if detected_drugs:
            drug_facts = self.query_openfda_drug(detected_drugs[0])

        return {
            "emergency": emergency_info,
            "detected_drugs": detected_drugs,
            "detected_conditions": detected_conditions,
            "clinical_trials": trials,
            "drug_facts": drug_facts
        }
