import os

def print_message(message, options):
    print("Q: "+message)
    print("A: Choose an option:")
    for i, option in enumerate(options, 1):
        print(f"   {i}. {option}")
    print(f"   {len(options) + 1}. Exit")

def interface(message, options):
    print_message(message, options)
    options_length = len(options) + 1

    while True:
        try:
            choice = int(input(f"Enter your choice (1, .., or {options_length}): "))
            if choice > 0 and choice < options_length:
                print()
                return options[choice - 1]
            elif choice == options_length:
                print("Exiting the program.\n")
                os._exit(0)
            else:
                print(f"Invalid choice. Please choose (1, .., or {options_length})\n")
        except ValueError:
            print(f"Invalid choice. Please choose (1, .., or {options_length})\n")

