from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext
import datetime

today = datetime.date.today()
today_str = today.strftime("%B %d, %Y")

# Dictionary to store handover notes
handover_notes = {
    "Issue": [],
    "On Progress": [],
    "Done": []
}

async def start(update: Update, context: CallbackContext) -> None:
    """Command to start the bot."""
    await update.message.reply_text(
        "Hello! I am your Handover Notes Bot.\n"
        "You can add notes to the following sections:\n"
        "- Issue\n"
        "- On Progress\n"
        "- Done\n\n"
        "Commands:\n"
        "- /show : Show all handover notes.\n"
    )
    await send_menu(update, context)

async def send_menu(update: Update, context: CallbackContext) -> None:
    """Send a menu with buttons to select the section to add notes."""
    keyboard = [
        [InlineKeyboardButton("Issue", callback_data="add_Issue")],
        [InlineKeyboardButton("On Progress", callback_data="add_On Progress")],
        [InlineKeyboardButton("Done", callback_data="add_Done")],
        [InlineKeyboardButton("Edit Note", callback_data="edit_note")],
        [InlineKeyboardButton("Move Note", callback_data="move_note")],
        [InlineKeyboardButton("Delete Note", callback_data="delete_note")],  # New delete button
        [InlineKeyboardButton("Show Notes", callback_data="show_notes")],
        [InlineKeyboardButton("Clear Notes", callback_data="clear_notes")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("Choose an action:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text("Choose an action:", reply_markup=reply_markup)

async def handle_menu_selection(update: Update, context: CallbackContext) -> None:
    """Handle the button clicks for selecting sections."""
    query = update.callback_query
    await query.answer()

    action = query.data
    current_message_text = query.message.text  # Save current message text

    if action.startswith("add_"):
        section = action.split("_")[1]
        context.user_data["selected_section"] = section

        # Check the selected section and show appropriate submenu
        if section == "Issue":
            await show_issue_submenu(update, context)
        elif section == "On Progress":
            await show_on_progress_submenu(update, context)
        elif section == "Done":
            await show_done_submenu(update, context)
        else:
            new_message_text = f"You selected: {section}. Please type your note."
            if current_message_text != new_message_text:
                await query.edit_message_text(new_message_text)  # Only edit if text changes
            context.user_data["awaiting_note"] = True

    elif action == "edit_note":
        await show_edit_menu(update, context)
    elif action == "delete_note":
        await show_delete_menu(update, context)  # Show delete menu
    elif action == "move_note":
        await show_move_menu(update, context)  # Show move menu
    elif action == "show_notes":
        await show_notes(update, context)
    elif action == "clear_notes":
        handover_notes["Issue"].clear()
        handover_notes["On Progress"].clear()
        handover_notes["Done"].clear()
        if current_message_text != "All notes have been cleared.":
            await query.edit_message_text("All notes have been cleared.")
        await send_menu(update, context)
    elif action == "cancel":
        if current_message_text != "Cancelled. Returning to main menu.":
            await query.edit_message_text("Cancelled. Returning to main menu.")  # Only edit if text changes
        await send_menu(update, context)  # Return to main menu when cancel is selected


async def show_issue_submenu(update: Update, context: CallbackContext) -> None:
    """Show a submenu for the 'Issue' section with two options: Add Issue or Cancel."""
    keyboard = [
        [InlineKeyboardButton("Add Issue", callback_data="add_issue_confirm")],
        [InlineKeyboardButton("Cancel", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text("You selected 'Issue'. What would you like to do?", reply_markup=reply_markup)

async def show_on_progress_submenu(update: Update, context: CallbackContext) -> None:
    """Show a submenu for the 'On Progress' section."""
    keyboard = [
        [InlineKeyboardButton("Add On Progress", callback_data="add_on progress_confirm")],
        [InlineKeyboardButton("Cancel", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text("You selected 'On Progress'. What would you like to do?", reply_markup=reply_markup)

async def show_done_submenu(update: Update, context: CallbackContext) -> None:
    """Show a submenu for the 'On Progress' section."""
    keyboard = [
        [InlineKeyboardButton("Add Done", callback_data="add_done_confirm")],
        [InlineKeyboardButton("Cancel", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text("You selected 'Done'. What would you like to do?", reply_markup=reply_markup)


async def show_delete_menu(update: Update, context: CallbackContext) -> None:
    """Show a menu for deleting notes from the sections."""
    keyboard = []
    for section, notes in handover_notes.items():
        if notes:
            keyboard.append([InlineKeyboardButton(f"Delete from {section}", callback_data=f"delete_{section}")])
    if not keyboard:
        await update.callback_query.message.reply_text("No notes available to delete.")
        await send_menu(update, context)
    else:
        keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])  # Add cancel button
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.reply_text("Choose a section to delete from:", reply_markup=reply_markup)


async def handle_delete_selection(update: Update, context: CallbackContext) -> None:
    """Handle selection of a section to delete from."""
    query = update.callback_query
    await query.answer()

    action = query.data.split("_")

    if action[0] == "delete":
        section = action[1]
        context.user_data["delete_section"] = section

        message = f"Current notes in {section}:\n"
        for idx, note in enumerate(handover_notes[section], start=1):
            message += f"  {idx}. {note}\n"
        if not handover_notes[section]:
            message += "  No notes available to delete.\n"
            await query.edit_message_text(message)
            await send_menu(update, context)
            return

        message += "\nPlease type the number of the note you want to delete."
        await query.edit_message_text(message)
        context.user_data["awaiting_delete_index"] = True


async def delete_note_message(update: Update, context: CallbackContext) -> None:
    """Handle the deletion of a specific note."""
    if context.user_data.get("awaiting_delete_index"):
        try:
            index = int(update.message.text) - 1
            section = context.user_data.get("delete_section")

            if 0 <= index < len(handover_notes[section]):
                deleted_note = handover_notes[section].pop(index)
                await update.message.reply_text(f"Note deleted from {section}: {deleted_note}")

                # Reset user data flags
                context.user_data["awaiting_delete_index"] = False
                context.user_data["delete_section"] = None

                # Show the menu again
                await send_menu(update, context)
            else:
                await update.message.reply_text("Invalid note number. Please try again.")
        except ValueError:
            await update.message.reply_text("Please enter a valid number.")
    else:
        await update.message.reply_text("Please use the menu to select a section first.")


async def add_note_message(update: Update, context: CallbackContext) -> None:
    """Add a note to the selected section from the user's message."""
    section = context.user_data.get("selected_section")  # Get the selected section
    note = update.message.text
    print(f"DEBUG: section={section}, note={note}")  # Tambahkan debugging
    
    # Convert section to proper case (capitalize first letter of each word)
    if section:
        section = section.title()  # Ubah menjadi format "Title Case" untuk konsistensi

    if context.user_data.get("awaiting_note"):
        if section and section in handover_notes:  # Pastikan key sesuai dengan dictionary
            handover_notes[section].append(note)
            await update.message.reply_text(f"Added to {section}: {note}")
        else:
            await update.message.reply_text("Invalid section. Please try again.")
        context.user_data["awaiting_note"] = False
        context.user_data["selected_section"] = None
        await send_menu(update, context)

async def show_notes(update: Update, context: CallbackContext) -> None:
    """Command to display all notes."""
    message = f"FMC Pipeline {today_str}\n\n"
    for section, notes in handover_notes.items():
        message += f"{section}:\n"
        if notes:
            for idx, note in enumerate(notes, start=1):
                message += f"  {idx}. {note}\n"
        else:
            message += "  -\n"
        message += "\n"

    # Check if the update is a message or a callback query
    if update.message:
        await update.message.reply_text(message)
    elif update.callback_query:
        await update.callback_query.message.edit_text(message)
    
    await send_menu(update, context)  # After showing the notes, send the menu again


async def show_edit_menu(update: Update, context: CallbackContext) -> None:
    """Show a menu for editing notes."""
    keyboard = []
    for section, notes in handover_notes.items():
        if notes:
            keyboard.append([InlineKeyboardButton(f"Edit {section}", callback_data=f"edit_{section}")])
    if not keyboard:
        await update.callback_query.message.reply_text("No notes available to edit.")
        await send_menu(update, context)  # Always show the main menu
    else:
        keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])  # Add cancel button
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.reply_text("Choose an action:", reply_markup=reply_markup)


async def handle_edit_selection(update: Update, context: CallbackContext) -> None:
    """Handle selection of a section to edit."""
    query = update.callback_query
    await query.answer()

    action = query.data.split("_")

    if action[0] == "edit":
        section = action[1]
        context.user_data["edit_section"] = section

        message = f"Current notes in {section}:\n"
        for idx, note in enumerate(handover_notes[section], start=1):
            message += f"  {idx}. {note}\n"
        if not handover_notes[section]:
            message += "  No notes available to edit.\n"
            await query.edit_message_text(message)
            await send_menu(update, context)  # Return to the menu if no notes are available
            return

        message += "\nPlease type the number of the note you want to edit."
        await query.edit_message_text(message)
        context.user_data["awaiting_edit_index"] = True


async def edit_note_message(update: Update, context: CallbackContext) -> None:
    """Handle the editing of a specific note."""
    if context.user_data.get("awaiting_edit_index"):
        try:
            index = int(update.message.text) - 1
            section = context.user_data.get("edit_section")

            if 0 <= index < len(handover_notes[section]):
                context.user_data["edit_index"] = index
                await update.message.reply_text(f"You selected note {index + 1}: {handover_notes[section][index]}\nPlease type the new text.")
                context.user_data["awaiting_edit_note"] = True
                context.user_data["awaiting_edit_index"] = False
            else:
                await update.message.reply_text("Invalid note number. Please try again.")
        except ValueError:
            await update.message.reply_text("Please enter a valid number.")

    elif context.user_data.get("awaiting_edit_note"):
        new_note = update.message.text
        section = context.user_data.get("edit_section")
        index = context.user_data.get("edit_index")

        handover_notes[section][index] = new_note
        await update.message.reply_text(f"Note updated in {section}: {new_note}")

        # Reset user data flags
        context.user_data["awaiting_edit_note"] = False
        context.user_data["edit_section"] = None
        context.user_data["edit_index"] = None

        # Show the menu again
        await send_menu(update, context)
    else:
        await update.message.reply_text("Please use the menu to select a section first.")

async def show_move_menu(update: Update, context: CallbackContext) -> None:
    """Show a menu for moving notes."""
    keyboard = []
    for section, notes in handover_notes.items():
        if notes:
            keyboard.append([InlineKeyboardButton(f"Move from {section}", callback_data=f"move_{section}")])
    if not keyboard:
        await update.callback_query.message.reply_text("No notes available to move.")
        await send_menu(update, context)
    else:
        keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])  # Add cancel button
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.reply_text("Choose a section to move from:", reply_markup=reply_markup)

async def handle_move_selection(update: Update, context: CallbackContext) -> None:
    """Handle the selection of a section to move from."""
    query = update.callback_query
    await query.answer()

    action = query.data.split("_")
    if action[0] == "move":
        section = action[1]
        context.user_data["move_section"] = section

        message = f"Current notes in {section}:\n"
        for idx, note in enumerate(handover_notes[section], start=1):
            message += f"  {idx}. {note}\n"

        if not handover_notes[section]:
            message += "  No notes available to move.\n"
            await query.edit_message_text(message)
            await send_menu(update, context)
            return

        message += "\nPlease type the number of the note you want to move."
        await query.edit_message_text(message)
        context.user_data["awaiting_move_index"] = True

async def move_note_message(update: Update, context: CallbackContext) -> None:
    """Handle moving a note to another section."""
    if context.user_data.get("awaiting_move_index"):
        try:
            index = int(update.message.text) - 1
            section = context.user_data.get("move_section")

            if 0 <= index < len(handover_notes[section]):
                note_to_move = handover_notes[section].pop(index)
                context.user_data["note_to_move"] = note_to_move

                # Ask for the target section
                keyboard = [[InlineKeyboardButton(s, callback_data=f"target_{s}")] for s in handover_notes.keys()]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("Select the target section:", reply_markup=reply_markup)

                context.user_data["awaiting_target_section"] = True
                context.user_data["awaiting_move_index"] = False
            else:
                await update.message.reply_text("Invalid note number. Please try again.")
        except ValueError:
            await update.message.reply_text("Please enter a valid number.")
    else:
        await update.message.reply_text("Please use the menu to select a section first.")

async def handle_target_selection(update: Update, context: CallbackContext) -> None:
    """Handle selection of target section for moving a note."""
    query = update.callback_query
    await query.answer()

    if context.user_data.get("awaiting_target_section"):
        target_section = query.data.split("_")[1]
        note_to_move = context.user_data.get("note_to_move")

        handover_notes[target_section].append(note_to_move)
        await query.edit_message_text(f"Moved note to {target_section}: {note_to_move}")

        # Reset user data flags
        context.user_data["awaiting_target_section"] = False
        context.user_data["note_to_move"] = None

        # Show the menu again
        await send_menu(update, context)


async def handle_text_message(update: Update, context: CallbackContext) -> None:
    """Handle text messages based on the current context.""" 
    if context.user_data.get("awaiting_edit_index"):
        await edit_note_message(update, context)
    elif context.user_data.get("awaiting_edit_note"):
        await edit_note_message(update, context)
    elif context.user_data.get("awaiting_note"):
        await add_note_message(update, context)
    elif context.user_data.get("awaiting_delete_index"):
        await delete_note_message(update, context)
    elif context.user_data.get("awaiting_move_index") or context.user_data.get("awaiting_target_section"):
        await move_note_message(update, context)
    else:
        await update.message.reply_text("Please use the menu to select a section first.")


def main():
    application = Application.builder().token("7647611180:AAHLpJl9zLlMvy7F7yYqaWNUTUc2yms8ffY").build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("show", show_notes))
    application.add_handler(CallbackQueryHandler(handle_menu_selection, pattern="^add_|edit_note$|show_notes$|clear_notes$|delete_note$|move_note$|cancel$"))
    application.add_handler(CallbackQueryHandler(handle_edit_selection, pattern="^edit_"))
    application.add_handler(CallbackQueryHandler(handle_delete_selection, pattern="^delete_"))
    application.add_handler(CallbackQueryHandler(handle_move_selection, pattern="^move_"))
    application.add_handler(CallbackQueryHandler(handle_target_selection, pattern="^target_"))
    application.add_handler(MessageHandler(filters.TEXT, handle_text_message))  # Handle all text input

    application.run_polling()

if __name__ == '__main__':
    main()
