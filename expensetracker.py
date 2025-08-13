import json
import os
from datetime import datetime

FILENAME = "expenses.json"

# If file doesn't exist, create it
if not os.path.exists(FILENAME):
    with open(FILENAME, "w") as file:
        json.dump([], file)

def load_data():
    with open(FILENAME, "r") as file:
        return json.load(file)

def save_data(data):
    with open(FILENAME, "w") as file:
        json.dump(data, file, indent=4)

def add_expense():
    amount = float(input("Enter amount: ₹ "))
    category = input("Enter category (food, travel, etc.): ")
    note = input("Any note (optional): ")

    entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "amount": amount,
        "category": category,
        "note": note
    }

    data = load_data()
    data.append(entry)
    save_data(data)
    print("✅ Expense added!\n")

def view_expenses():
    data = load_data()
    if not data:
        print("⚠️ No expenses found.\n")
        return

    print("\n📄 Your Expenses:")
    print("Date & Time\t\tAmount\tCategory\tNote")
    print("-"*50)
    for exp in data:
        print(f"{exp['date']}\t₹{exp['amount']:.2f}\t{exp['category']}\t{exp['note']}")

def total_expense():
    data = load_data()
    total = sum(exp["amount"] for exp in data)
    print(f"\n💰 Total Expenses: ₹{total:.2f}\n")

def menu():
    while True:
        print("\n====== EXPENSE TRACKER 💾 (JSON) ======")
        print("1. Add Expense")
        print("2. View Expenses")
        print("3. View Total Expense")
        print("4. Exit")

        choice = input("Choose an option (1–4): ")

        if choice == "1":
            add_expense()
        elif choice == "2":
            view_expenses()
        elif choice == "3":
            total_expense()
        elif choice == "4":
            print("👋 Bye bro! Stay financially smart 💸")
            break
        else:
            print("❌ Invalid choice. Try again.\n")

if __name__ == "__main__":
    menu()
