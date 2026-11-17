import asyncio
import json
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    KeyboardButton,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

BOT_TOKEN = os.environ["BOT_TOKEN"]      # токен от @BotFather
WEBAPP_URL = os.environ["WEBAPP_URL"]    # HTTPS-ссылка на index.html

# id и цены (в звёздах) должны совпадать с CATALOG в index.html
CATALOG = {
    "guide": {"title": "Гайд (PDF)", "price": 50,
              "delivery": "Ваш гайд: https://example.com/guide.pdf"},
    "templates": {"title": "Набор шаблонов", "price": 120,
                  "delivery": "Ваши шаблоны: https://example.com/templates.zip"},
    "access": {"title": "Закрытый чат", "price": 200,
               "delivery": "Ссылка-приглашение: https://t.me/+your_invite_link"},
}

dp = Dispatcher()


def parse_cart(raw: dict) -> dict:
    """Оставляем только известные товары и разумное количество."""
    cart = {}
    for pid, qty in raw.items():
        if pid in CATALOG and isinstance(qty, int) and 0 < qty <= 20:
            cart[pid] = qty
    return cart


@dp.message(Command("start"))
async def start(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Открыть магазин", web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True,
    )
    await message.answer("Добро пожаловать! Нажмите кнопку, чтобы открыть магазин.", reply_markup=kb)


@dp.message(Command("paysupport"))
async def paysupport(message: Message):
    # Telegram требует, чтобы у платёжного бота была эта команда
    await message.answer("Вопросы по оплате и возвраты: напишите @your_username")


@dp.message(F.web_app_data)
async def on_order(message: Message):
    try:
        cart = parse_cart(json.loads(message.web_app_data.data))
    except (ValueError, AttributeError):
        cart = {}
    if not cart:
        await message.answer("Корзина пуста или заказ не распознан. Попробуйте ещё раз.")
        return

    total = sum(CATALOG[p]["price"] * q for p, q in cart.items())  # цену считаем на сервере
    lines = ", ".join(f'{CATALOG[p]["title"]} × {q}' for p, q in cart.items())
    payload = ",".join(f"{p}:{q}" for p, q in cart.items())  # до 128 байт

    # Для Stars: валюта XTR, пустой provider_token и ровно одна позиция в prices
    await message.answer_invoice(
        title="Ваш заказ",
        description=lines[:255],
        payload=payload,
        currency="XTR",
        prices=[LabeledPrice(label="Заказ", amount=total)],
    )


@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@dp.message(F.successful_payment)
async def paid(message: Message):
    payment = message.successful_payment
    # Сохраните payment.telegram_payment_charge_id: он нужен для возврата Stars
    for part in payment.invoice_payload.split(","):
        pid, _, qty = part.partition(":")
        if pid in CATALOG:
            await message.answer(CATALOG[pid]["delivery"])
    await message.answer("Спасибо за покупку!")


async def main():
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
