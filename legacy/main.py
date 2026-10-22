"""
Weather Data Analyzer

This file contains the main menu for the project. It connects the
fetching, analyzing, and visualizing parts of the application.
"""

from analyze import analyze_weather_data
from fetch_weather import fetch_and_save_weather
from visualize import create_weather_graphs


def show_menu():
    """Display the menu options for the user."""
    print("\n===== Weather Data Analyzer =====")
    print("1. Fetch Weather Data")
    print("2. Analyze Weather Data")
    print("3. Visualize Weather Data")
    print("4. Exit")


def main():
    """Run the menu-driven weather analyzer program."""
    while True:
        show_menu()
        choice = input("Enter your choice (1-4): ").strip()

        if choice == "1":
            city = input("Enter city name: ").strip()

            if city:
                fetch_and_save_weather(city)
            else:
                print("City name cannot be empty. Please try again.")

        elif choice == "2":
            analyze_weather_data()

        elif choice == "3":
            create_weather_graphs()

        elif choice == "4":
            print("Thank you for using Weather Data Analyzer. Goodbye!")
            break

        else:
            print("Invalid choice. Please enter a number from 1 to 4.")


if __name__ == "__main__":
    main()
