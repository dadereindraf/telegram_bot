from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext

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
        [InlineKeyboardButton("Show Notes", callback_data="show_notes")],
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

    if action.startswith("add_"):
        section = action.split("_")[1]
        context.user_data["selected_section"] = section
        await query.edit_message_text(f"You selected: {section}. Please type your note.")
        context.user_data["awaiting_note"] = True
    elif action == "edit_note":
        await show_edit_menu(update, context)
    elif action == "show_notes":
        await show_notes(update, context)

async def add_note_message(update: Update, context: CallbackContext) -> None:
    """Add a note to the selected section from the user's message."""
    if context.user_data.get("awaiting_note"):
        section = context.user_data.get("selected_section")
        note = update.message.text

        if section in handover_notes:
            handover_notes[section].append(note)
            await update.message.reply_text(f"Added to {section}: {note}")
        else:
            await update.message.reply_text("Invalid section. Please try again.")

        # Reset user data flags
        context.user_data["awaiting_note"] = False
        context.user_data["selected_section"] = None

        # Show the menu again
        await send_menu(update, context)
    else:
        await update.message.reply_text("Please use the menu to select a section first.")

async def show_notes(update: Update, context: CallbackContext) -> None:
    """Command to display all notes."""
    message = "Handover Notes:\n\n"
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

async def handle_text_message(update: Update, context: CallbackContext) -> None:
    """Handle text messages based on the current context.""" 
    if context.user_data.get("awaiting_edit_index"):
        await edit_note_message(update, context)
    elif context.user_data.get("awaiting_edit_note"):
        await edit_note_message(update, context)
    elif context.user_data.get("awaiting_note"):
        await add_note_message(update, context)
    else:
        await update.message.reply_text("Please use the menu to select a section first.")

def main():
    application = Application.builder().token("7647611180:AAHLpJl9zLlMvy7F7yYqaWNUTUc2yms8ffY").build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("show", show_notes))
    application.add_handler(CallbackQueryHandler(handle_menu_selection, pattern="^add_|edit_note$|show_notes$"))
    application.add_handler(CallbackQueryHandler(handle_edit_selection, pattern="^edit_"))
    application.add_handler(MessageHandler(filters.TEXT, handle_text_message))

    application.run_polling()

if __name__ == '__main__':
    main()
