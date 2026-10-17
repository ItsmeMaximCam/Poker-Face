from game import play_hand, table
from recorder import start_camera

start_camera()

while True:
    play_hand()
    
    if table["player"] == 0:
        print("\nYou're out of chips! Game Over!")
        break
    
    if table["ai"] == 0:
        print("\nYou rinsed out the AI! You win!")
        break

    again = input("\nPlay again? (y/n): ").lower()
    
    if again != "y":
        break