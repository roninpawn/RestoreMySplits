from LSSFile import *
import tkinter.filedialog

# Use GUI to Open/Save Files
tk_root = tkinter.Tk()
tk_root.wm_attributes('-topmost', 1)
tk_root.withdraw()

# Open file dialogue
print("\r\nSelect splits file to open in GUI.")
splits_file = tkinter.filedialog.askopenfilename(filetypes=[("Livesplit LSS", ".lss .bak"), ("All files", ".*")])
if splits_file == "": quit()
print(f"Opening '{splits_file}'.")

# Instantiate LSSFile
my_lss = LSSFile(splits_file)
if not my_lss.is_loaded(): quit()

# Display a list of runs that still seem restorable after compatibility culling.
restore_id = "None"
attempts = 5
while not my_lss.is_restorable(restore_id):
    if attempts > 4:
        attempts = 0
        print(f"Listing all apparently valid runs.\r\n\r\n{my_lss.show_attempts()}\r\n")

    restore_id = input("Choose a run to restore by its ID: [q=quit] ").strip()
    if restore_id.lower() == "q":
        my_lss.close()
        quit()
    attempts += 1
print(f"... Attempting to restore run # {restore_id} ...\r\n")

# Deep-analyze run for viable restoration, fixing errors & missing splits, where possible.
plan_success = my_lss.make_plan(restore_id)
if plan_success < 0:
    print(f"ERROR: Run {restore_id} is not restorable. [Code {-plan_success}]")
    my_lss.close()
    quit()

# Display a list of all proposed changes to the "Personal Best" speedrun in the file.
print("---Proposed alterations to each segment---")
print(my_lss.show_plan())
if plan_success == 0:
    print("\r\nWARNING: Multiple missing/skipped splits detected. Accurate restoration is uncertain.\r\n"
          "Carefully review the proposed changes.")

# Save changes if user agrees.
confirm_save = input("\r\nWould you like to save these changes? [y/n] ").strip()
if confirm_save.lower() == "y":
    print("Select where to save to in the 'Save As...' window.\r\n")
    save_to = tkinter.filedialog.asksaveasfilename(filetypes=[("Livesplit LSS", ".lss .bak"), ("All files", ".*")])
    if save_to != "":
        print("Saving...")
        success = my_lss.save_plan(save_to)
        if success < 1: print(f"ERROR: Save failed. [Code {-success}]")
        else: print(f"Changes successfully saved to '{save_to}'.")
    else: print("Save cancelled.")

my_lss.close()
