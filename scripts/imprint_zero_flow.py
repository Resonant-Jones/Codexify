#!/usr/bin/env python3
"""
Imprint Zero Flow Script
----------------------
Interactive CLI for guiding users through companion creation.
"""

import sys
from typing import List

from guardian.agents.imprint_zero import imprint_zero

def print_options(options: List[str]) -> None:
    """Print numbered options."""
    if options:
        print("\nOptions:")
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        print()

def main() -> None:
    """Run the Imprint Zero flow."""
    try:
        # Start flow
        prompt, options = imprint_zero.start_flow()
        print(f"\n{prompt}")
        
        while True:
            print_options(options)
            
            if not options:
                user_input = input("> ")
            else:
                try:
                    choice = int(input("Enter option number (or 0 to quit): "))
                    if choice == 0:
                        print("\nFlow cancelled. Progress saved as draft.")
                        sys.exit(0)
                    user_input = options[choice - 1]
                except (ValueError, IndexError):
                    print("Invalid option. Please try again.")
                    continue
            
            # Process step
            prompt, options, is_complete = imprint_zero.process_step(user_input)
            print(f"\n{prompt}")
            
            if is_complete:
                if "Save" in options or "Deploy" in options:
                    # Final review
                    print_options(options)
                    choice = input("Enter option: ").lower()
                    
                    if choice in ['s', 'save', '2']:
                        name = input("\nEnter name for your companion: ")
                        file_path = imprint_zero.save_companion(name)
                        print(f"\nCompanion saved to: {file_path}")
                        break
                    elif choice in ['d', 'deploy', '3']:
                        name = input("\nEnter name for your companion: ")
                        file_path = imprint_zero.save_companion(name)
                        print(f"\nCompanion saved to: {file_path}")
                        print("To deploy: guardianctl deploy-companion", name)
                        break
                    elif choice in ['e', 'edit', '1']:
                        # Restart from step 2
                        imprint_zero.current_flow["step"] = 1
                        prompt, options, _ = imprint_zero.process_step("edit")
                        print(f"\n{prompt}")
                        continue
                    else:
                        print("Invalid choice. Saving as draft.")
                        break
                else:
                    break

    except KeyboardInterrupt:
        print("\nFlow cancelled. Progress saved as draft.")
        sys.exit(1)

if __name__ == "__main__":
    main()
