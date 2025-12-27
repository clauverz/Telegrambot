import asyncio
import os
import logging
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from google import genai
from dotenv import load_dotenv

# 1. Setup Logging
logging.basicConfig(level=logging.INFO)

# 2. Load Environment Variables
load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Inisialisasi
if not GEMINI_KEY or not TOKEN:
    print("Error: Pastikan GEMINI_API_KEY dan TELEGRAM_TOKEN ada di file .env")
    exit()

client = genai.Client(api_key=GEMINI_KEY)
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)

# Konfigurasi Path Foto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
photo_path = os.path.join(BASE_DIR, "img", "007.jpg")

# --- State Management untuk Game ---
class GameState(StatesGroup):
    in_game = State()

# --- FUNGSI HELPER ---
def log_to_terminal(message: types.Message, reply_text: str):
    user = message.from_user
    full_name = user.full_name
    username = f"(@{user.username})" if user.username else ""
    text = message.text or "[Pesan bukan teks]"
    print(f"\n{'='*40}")
    print(f"📩 PESAN MASUK dari: {full_name} {username}")
    print(f"💬 Isi Pesan: {text}")
    print(f"🤖 Balasan Bot: {reply_text}")
    print(f"{'='*40}")

async def get_gemini_reply(prompt: str) -> str:
    try:
        loop = asyncio.get_event_loop()
        def call_gemini():
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    'system_instruction': (
                        "Kamu adalah Miumiu-Bot, asisten pribadi yang ramah, puitis, dan cerdas dan ketika ada yang bertanya pakai gombalan saja seperti baiklah cantik, tuan putri. "
                        "Gunakan bahasa Indonesia yang gaul namun tetap sopan. "
                        "Jika ditanya hal romantis, jawablah dengan sangat manis."
                        "lalu jika dia sekedar menyapa jangan terlalu di jawab panjang sekali langsung goda dan ke intinya saja"
                    ),
                    'temperature': 0.7,
                }
            )
            return response.text
        return await loop.run_in_executor(None, call_gemini)
    except Exception as e:
        logging.error(f"Gemini Error: {e}")
        if "429" in str(e):
            return "Waduh, aku sudah terlalu banyak menjawab hari ini. Coba lagi sebentar lagi ya (Limit API tercapai) 😅"
        return "Maaf, otak AI-ku sedang mengalami kendala teknis."

# --- FUNGSI FITUR ---
async def send_special_photo(message: types.Message):
    reply_log = "[MENGIRIM FOTO]"
    if os.path.exists(photo_path):
        photo = FSInputFile(photo_path)
        try:
            caption_text = "Menurutku dia, dia adalah seseorang yang sangat cantik manis dan lucu, dia bernama Friska Desiane Fauziah💖"
            await message.answer_photo(photo, caption=caption_text)
            log_to_terminal(message, f"{reply_log} - {caption_text}")
        except Exception as e:
            await message.answer("Gagal mengirim foto karena kendala teknis.")
            logging.error(f"Error Send Photo: {e}")
    else:
        await message.answer("Maaf, fotonya tidak ditemukan di server bot.")
        log_to_terminal(message, "Error: Foto tidak ditemukan")

# --- KEYBOARD INTERAKTIF ---
main_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Mulai Game Tebak Angka", callback_data="start_game")],
        [InlineKeyboardButton(text="🖼️ Kirim Foto Spesial", callback_data="send_special_photo")]
    ]
)

# --- HANDLER PERINTAH (COMMANDS) ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    reply = "Halo 👋 Aku Miumiu-Bot!\nAda yang bisa kubantu? Kamu bisa pilih menu di bawah atau langsung ketik pertanyaanmu."
    await message.answer(reply, reply_markup=main_keyboard)
    log_to_terminal(message, reply)

# --- HANDLER UNTUK GAME TEBAK ANGKA ---
async def start_game_handler(message: types.Message, state: FSMContext):
    secret_number = random.randint(1, 100)
    await state.update_data(secret_number=secret_number, attempts=0)
    await state.set_state(GameState.in_game)
    reply = "Baiklah, tuan putri! Aku sudah memilih sebuah angka rahasia antara 1 dan 100. Coba tebak!"
    await message.answer(reply)
    log_to_terminal(message, reply)

@dp.message(GameState.in_game, F.text)
async def process_guess_handler(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Itu bukan angka, cantik. Coba masukkan angka ya.")
        return

    guess = int(message.text)
    user_data = await state.get_data()
    secret_number = user_data['secret_number']
    
    if guess < secret_number:
        reply = "Angkanya terlalu rendah cantikku, coba lagi!"
        await message.answer(reply)
    elif guess > secret_number:
        reply = "Terlalu tinggi sayangg, ayo tebak lagi!"
        await message.answer(reply)
    else:
        reply = f"✨ KERENN BANGETT PUTRII AKUU! YEYY Angka rahasianyaa adalahh {secret_number}. Kamu menang! ✨"
        await message.answer(reply)
        await state.clear() # Mengakhiri game
    
    log_to_terminal(message, reply)

# --- HANDLER UNTUK CALLBACK QUERY (TOMBOL) ---
@dp.callback_query()
async def on_button_press(callback: CallbackQuery, state: FSMContext):
    if callback.data == "start_game":
        await callback.answer("Oke, game dimulai!")
        await start_game_handler(callback.message, state)
    elif callback.data == "send_special_photo":
        await callback.answer("Tentu, ini dia fotonya!")
        await send_special_photo(callback.message)

# --- HANDLER TEKS BIASA (LEGACY & TRIGGER) ---
@dp.message(F.text.casefold() == "hai")
async def hai_text(message: types.Message):
    reply = "Hai juga! 👋"
    await message.answer(reply)
    log_to_terminal(message, reply)

@dp.message(lambda msg: msg.text and "wanita tercantik di cianjur" in msg.text.lower())
async def wanita_tercantik_trigger(message: types.Message):
    await send_special_photo(message)

# --- AI HANDLER (Untuk semua pesan teks lainnya) ---
@dp.message(F.text)
async def ai_handler(message: types.Message):
    await bot.send_chat_action(message.chat.id, "typing")
    reply = await get_gemini_reply(message.text)
    await message.answer(reply)
    log_to_terminal(message, reply)

# 4. Fungsi Utama untuk Menjalankan Bot
async def main():
    print("\n" + "="*40)
    print("Miumiu Bot sedang berjalan...")
    print("Monitoring chat aktif di terminal ini.")
    print("="*40 + "\n")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot dimatikan oleh pengguna.")