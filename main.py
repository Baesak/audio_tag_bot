"""Chatbot for Telegram."""

from os import remove, getenv
from re import search
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, MessageHandler, \
    Filters, ConversationHandler, Updater, CommandHandler, CallbackQueryHandler
import mutagen
from pydub import AudioSegment
from dotenv import load_dotenv

TITLE, ARTIST, ASK, WRITE = range(4)


class TagBot:
    """Bot that can change 'title' and 'artist' tags in audio files.
     Supports english and russian language."""

    all_lang_strings = {
            'en': {
                "bot_descr": "Hi. I can change 'title' and 'artist' tags in your audiofile!\n"
                             "To do so - send any audio file to me.\n"
                             "Note: if you send with an extension other than mp3, "
                             "bot will convert your audio file in mp3.",
                "artist": "Enter artist.",
                "title": "Enter title.",
                "wrong_tag": "You should send text!",
                "wrong_audio": "You should send audio!",
                "lang_chosen": "English has been selected.\n"
                               "To get help with the bot, enter - /help.\n"
                               "To call language change panel, enter - /start.\n"
                               "Say 'thanks' - /thanks",
                "choose_lang": "Choose language:",
                "wrong_choice": "You should click on button!",
                "help_thanks": "You can say 'thanks' to developer with /thanks",
                "thanks": "You can send your 'thanks' to developer!\n"
                          "It will be saved in 'thanklist' with your nickname.\n"
                          "Do you want to do it?",
                "yes": "Yes",
                "no": "No",
                "not_saved": "Your 'thanks' was not saved.",
                "saved": "Your 'thanks' was saved.",
                "thx_again": "You have said thanks already."
            },
            'ru': {
                "bot_descr": "Привет. Я могу менять теги «название» и"
                             " «исполнитель» в вашем аудиофайле!\n"
                             "Для этого пришлите мне любой аудиофайл.\n"
                             "Примечание: если вы отправляете с расширением, отличным от mp3, "
                             "бот сконвертирует ваш аудиофайл в mp3.",
                "artist": "Введите исполнителя.",
                "title": "Введите название.",
                "wrong_tag": "Вы должны вводить текст!",
                "wrong_audio": "Вы должны отправлять аудио!",
                "lang_chosen": "Был выбран русский язык. "
                               "Чтобы получить помощь по работе бота введите - /help.\n"
                               "Чтобы вызвать панель смены языка введите - /start.\n"
                               "Cказать 'спасибо' - /thanks",
                "choose_lang": "Выберите язык:",
                "wrong_choice": "Вы должны нажать на кнопку!",
                "help_thanks": "Вы можете поблагодарить разработчика с помощью /thanks",
                "thanks": "Вы можете отправить своё 'спасибо' разработчику!\n"
                          "Оно будет сохранено в 'списке благодарностей' вместе с вашим никнеймом.\n"
                          "Вы хотите сделать это?",
                "yes": "Да",
                "no": "Нет",
                "not_saved": "Ваше спасибо не было сохранено.",
                "saved": "Ваше спасибо было сохранено.",
                "thx_again": "Вы уже говорили спасибо.",
            }
        }

    def __init__(self):

        load_dotenv()
        self._tags = {'title': "", 'artist': "", 'filename': ""}
        self.updater = Updater(token=getenv("token"))
        self.dispatcher = self.updater.dispatcher
        self.strings = {}  # 'strings' storing strings of current language.
        self.strings = self.all_lang_strings["en"]

        self._add_handlers()
        self.updater.start_polling()

    def _add_handlers(self):

        change_tag_conv = ConversationHandler(
            entry_points=[MessageHandler(Filters.audio, self.take_audio_message)],
            states={
                TITLE: [MessageHandler(Filters.text, self.take_title)],
                ARTIST: [MessageHandler(Filters.text, self.take_artist)],
            },
            fallbacks=[MessageHandler(Filters.all, self.wrong_data_conversation)]
        )

        self.dispatcher.add_handler(CommandHandler("thanks", self.thanks_handler))
        self.dispatcher.add_handler(CallbackQueryHandler(self.lang_buttons, pattern="en|ru"))
        self.dispatcher.add_handler(CallbackQueryHandler(self.thanks_no_button, pattern="False"))
        self.dispatcher.add_handler(CallbackQueryHandler(self.thanks_yes_button, pattern="True"))
        self.dispatcher.add_handler(CommandHandler("start", self.start_command))
        self.dispatcher.add_handler(CommandHandler("help", self.help_command))
        self.dispatcher.add_handler(change_tag_conv)
        self.dispatcher.add_handler(MessageHandler(Filters.all, self.wrong_data))

    def wrong_choice(self, update: Update, context: CallbackContext):
        """Send message if user send something when he should click on button."""

        self._send_message(self.strings["wrong_choice"], update, context)

    def wrong_data(self, update: Update, context: CallbackContext):
        """Send message if user send something else when he should send audio."""
        if update.message.text in ["Thank you", "Спасибо", "Thanks", "Thx", "Спс", "thanks", "thank you",
                                   "thx", "спасибо", "спс"]:
            self._send_message(self.strings["help_thanks"], update, context)
        else:
            self._send_message(self.strings["wrong_audio"], update, context)

    def thanks_handler(self, update: Update, context: CallbackContext):
        """Prompts the user to thank the author. Sets keyboard"""

        keyboard = [
            [
                InlineKeyboardButton(self.strings["yes"], callback_data="True"),
                InlineKeyboardButton(self.strings["no"], callback_data="False"),
            ],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(self.strings["thanks"], reply_markup=reply_markup)

    def thanks_no_button(self, update: Update, context: CallbackContext):
        """Send message if user refused to say 'thanks'"""

        self._send_message(self.strings["not_saved"], update, context)

    def thanks_yes_button(self, update: Update, context: CallbackContext):
        """Check is user already said yes. If he is - just sends message. If not - writes
         his username in 'thanks' list and sends message"""

        with open("thanks_list.txt", "r+") as file:
            name = update.callback_query.from_user.username

            if bool(search(name, file.read())):
                self._send_message(self.strings["thx_again"], update, context)
            else:
                file.write(f"Thanks from {update.callback_query.from_user.username}!\n")
                self._send_message(self.strings["saved"], update, context)

    def start_command(self, update: Update, context: CallbackContext):
        """Sends a language choose message with 2 inline buttons attached."""
        keyboard = [
            [
                InlineKeyboardButton("English", callback_data="en"),
                InlineKeyboardButton("Русский", callback_data="ru"),
            ],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(self.strings["choose_lang"], reply_markup=reply_markup)

    def lang_buttons(self, update: Update, context: CallbackContext):
        """Parses the CallbackQuery and updates current language."""
        query = update.callback_query
        query.answer()

        self.strings = self.all_lang_strings[query.data]

        self._send_message(self.strings["lang_chosen"], update, context)

        return ConversationHandler.END

    def help_command(self, update: Update, context: CallbackContext):
        """Displays info on how to use the bot."""
        self._send_message(self.strings["bot_descr"], update, context)

    def wrong_data_conversation(self, update: Update, context: CallbackContext):
        """Send message if user send something else when he should send tag name."""

        self._send_message(self.strings["wrong_text"], update, context)

    def take_audio_message(self, update: Update, context: CallbackContext):
        """Save audio file from user, and asks to enter new title."""

        audio = update.message.audio

        with open(f"{audio.file_name}", "wb") as file:
            context.bot.get_file(audio).download(out=file)
        self._tags["filename"] = audio.file_name

        update.message.reply_text(self.strings["title"])
        return TITLE

    def take_title(self, update: Update, context: CallbackContext):
        """Saves new title and asks to enter new artist name."""

        self._tags["title"] = update.message.text
        update.message.reply_text(self.strings["artist"])
        return ARTIST

    def take_artist(self, update, context):
        """Saves new artist name and call 'send_new_audio'"""
        self._tags["artist"] = update.message.text
        self.send_new_audio(update, context)
        return ConversationHandler.END

    def send_new_audio(self, update, context):
        """Call 'change_tag' and sends new audio to user. If file extension is not mp3 -
        calls 'convert_to_mp3'. Deletes audio file after everything is done."""

        if not self._tags["filename"].lower().endswith("mp3"):
            self.convert_to_mp3()
        self.change_tag()

        with open(self._tags["filename"], "rb") as file:
            context.bot.send_audio(chat_id=update.effective_chat.id, audio=file)

        remove(self._tags["filename"])
        self._tags = self._tags.fromkeys(self._tags, None)

    def convert_to_mp3(self):
        """Creating new audio file with mp3 extension using 'pydub'. Deletes
        old file and changes 'filename' tag in 'self.tags'."""

        filename = self._tags["filename"]
        new_name = "".join(filename.split(".")[:-1]) + ".mp3"

        audio = AudioSegment.from_file(filename)
        audio.export(new_name, format="mp3", bitrate="320k")

        remove(filename)
        self._tags["filename"] = new_name

    def change_tag(self):
        """Changing tags in audio file using 'mutagen'"""

        media_file = mutagen.File(self._tags["filename"], easy=True)
        media_file['title'] = self._tags["title"]
        media_file['artist'] = self._tags["artist"]
        media_file.save()

    @staticmethod
    def _send_message(text, update, context):
        """Shortcut for 'context.bot.send_message'."""

        context.bot.send_message(chat_id=update.effective_chat.id, text=text)


if __name__ == "__main__":
    my_tag_bot = TagBot()
