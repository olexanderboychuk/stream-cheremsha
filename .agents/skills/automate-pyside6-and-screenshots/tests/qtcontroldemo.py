#!/usr/bin/env python3
"""Demo automation script for the PyQtAuto demo application.

This script demonstrates how to automate a PySide6 application using
the PyQtAuto client. It performs various actions and captures screenshots
to verify the results.

Usage:
    1. First, start the demo app:
       python tests/qtappdemo.py

    2. Then run this automation script:
       python tests/qtcontroldemo.py
"""

from pathlib import Path

from pyqtauto import PyQtAutoClient


def main():
    """Run the automation demo."""
    # Create output directory for screenshots
    output_dir = Path(__file__).parent / "screenshots"
    output_dir.mkdir(exist_ok=True)

    print("Connecting to PyQtAuto server...")

    with PyQtAutoClient(port=9876) as client:
        print("Connected!")

        # Wait for app to be ready
        client.wait_idle()

        # === Step 1: Explore the widget tree ===
        print("\n=== Widget Tree ===")
        tree = client.get_tree(depth=2)
        print(f"Root window: {tree.get('objectName')} ({tree.get('class')})")
        print(f"Children: {len(tree.get('children', []))}")

        # Take initial screenshot
        print("\nTaking initial screenshot...")
        client.screenshot_to_file(output_dir / "01_initial.png")
        print(f"Saved: {output_dir / '01_initial.png'}")

        # === Step 2: Fill out the form ===
        print("\n=== Filling out the form ===")

        # Type name
        print("Typing name...")
        client.type("@name:name_input", "John Doe")
        client.sleep(200)

        # Type email
        print("Typing email...")
        client.type("@name:email_input", "john.doe@example.com")
        client.sleep(200)

        # Select country
        print("Selecting country...")
        # First click to open the combo
        client.click("@name:country_combo")
        client.sleep(200)
        # Set the value
        client.set_value("@name:country_combo", "France")
        client.sleep(200)

        # Set age
        print("Setting age...")
        client.set_value("@name:age_spinner", 30)
        client.sleep(200)

        # Select gender
        print("Selecting gender...")
        client.click("@name:radio_female")
        client.sleep(200)

        # Check newsletter
        print("Checking newsletter...")
        client.check("@name:newsletter_check", True)
        client.sleep(200)

        # Take form screenshot
        print("\nTaking form screenshot...")
        client.screenshot_to_file(output_dir / "02_form_filled.png")
        print(f"Saved: {output_dir / '02_form_filled.png'}")

        # Submit form
        print("Submitting form...")
        client.click("@name:submit_btn")
        client.sleep(500)

        # Take result screenshot
        print("\nTaking result screenshot...")
        client.screenshot_to_file(output_dir / "03_form_submitted.png")
        print(f"Saved: {output_dir / '03_form_submitted.png'}")

        # Verify result
        result_text = client.get_text("@name:result_label")
        print(f"Result: {result_text}")

        # === Step 3: Test the counter ===
        print("\n=== Testing the counter ===")

        # Switch to Actions tab
        client.set_value("@name:main_tabs", 1)  # Tab index 1
        client.sleep(300)

        # Click increment a few times
        print("Incrementing counter...")
        for _i in range(5):
            client.click("@name:inc_btn")
            client.sleep(100)

        # Take counter screenshot
        print("\nTaking counter screenshot...")
        client.screenshot_to_file(output_dir / "04_counter.png")
        print(f"Saved: {output_dir / '04_counter.png'}")

        # Verify counter
        counter_value = client.get_text("@name:counter_label")
        print(f"Counter value: {counter_value}")

        # Click decrement
        print("Decrementing counter...")
        client.click("@name:dec_btn")
        client.click("@name:dec_btn")
        client.sleep(200)

        counter_value = client.get_text("@name:counter_label")
        print(f"Counter value after decrement: {counter_value}")

        # === Step 4: Test the slider ===
        print("\n=== Testing the slider ===")

        # Set slider value
        print("Setting slider to 75...")
        client.set_value("@name:volume_slider", 75)
        client.sleep(300)

        # Take slider screenshot
        print("\nTaking slider screenshot...")
        client.screenshot_to_file(output_dir / "05_slider.png")
        print(f"Saved: {output_dir / '05_slider.png'}")

        # Verify slider
        volume_text = client.get_text("@name:volume_label")
        print(f"Volume value: {volume_text}")

        # === Step 5: Test the progress bar ===
        print("\n=== Testing the progress bar ===")

        # Start progress
        print("Starting progress...")
        client.click("@name:start_progress_btn")
        client.sleep(1000)  # Wait for some progress

        # Take progress screenshot
        print("\nTaking progress screenshot...")
        client.screenshot_to_file(output_dir / "06_progress.png")
        print(f"Saved: {output_dir / '06_progress.png'}")

        # Stop progress
        print("Stopping progress...")
        client.click("@name:stop_progress_btn")
        client.sleep(200)

        # === Step 6: Test the list ===
        print("\n=== Testing the list ===")

        # Switch to Lists tab
        client.set_value("@name:main_tabs", 2)  # Tab index 2
        client.sleep(300)

        # Add new items
        print("Adding items to list...")
        for item in ["Test Item A", "Test Item B", "Test Item C"]:
            client.type("@name:new_item_input", item)
            client.click("@name:add_item_btn")
            client.sleep(200)

        # Take list screenshot
        print("\nTaking list screenshot...")
        client.screenshot_to_file(output_dir / "07_list.png")
        print(f"Saved: {output_dir / '07_list.png'}")

        # === Step 7: Test the text area ===
        print("\n=== Testing the text area ===")

        # Type notes
        print("Typing notes...")
        client.type(
            "@name:notes_text",
            "This is a test of the notes area.\n\n"
            "The PyQtAuto library allows you to:\n"
            "- Automate PySide6 applications\n"
            "- Take screenshots for verification\n"
            "- Interact with any widget\n\n"
            "This text was typed automatically!",
        )
        client.sleep(300)

        # Take final screenshot
        print("\nTaking final screenshot...")
        client.screenshot_to_file(output_dir / "08_notes.png")
        print(f"Saved: {output_dir / '08_notes.png'}")

        # === Summary ===
        print("\n" + "=" * 50)
        print("AUTOMATION COMPLETE!")
        print("=" * 50)
        print(f"\nScreenshots saved to: {output_dir}")
        print("\nTests performed:")
        print("  - Explored widget tree")
        print("  - Filled and submitted form")
        print("  - Used counter buttons")
        print("  - Adjusted slider")
        print("  - Started/stopped progress bar")
        print("  - Added items to list")
        print("  - Typed text in notes area")
        print("  - Captured 8 screenshots")

        # Optional: quit the app
        # print("\nQuitting application...")
        # client.quit()


if __name__ == "__main__":
    main()
