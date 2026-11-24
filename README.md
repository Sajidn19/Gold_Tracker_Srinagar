# Srinagar Gold Price Telegram Bot

Personal bot for Sajid Noor. Sends a daily gold price at 10:30 AM IST, focused on Srinagar / India, with international price and the factors moving it.

## Commands
- `/start` - welcome and subscribe to daily update
- `/price` - 24K / 22K / 18K per gram and per 10g
- `/srinagar` - Srinagar buying note (hallmark, HUID, making charges, GST)
- `/factors` - why gold goes up and down, simple language
- `/sources` - IBJA, MCX, RBI, World Gold Council
- `/daily` - daily update on/off

## Setup - 5 minutes, only you can do step 1

1. **Create the bot on Telegram (your account only)**
   - Open Telegram, search `@BotFather`, send `/newbot`
   - Name it e.g. `Sajid Gold Price Srinagar`, username e.g. `sajid_gold_srinagar_bot` (must end in `bot`)
   - BotFather gives you a token like `123456:ABC...` - keep it secret, do not share it in chat

2. **Run it**
   ```bash
   cd gold-price-telegram-bot
   pip install -r requirements.txt
   TELEGRAM_BOT_TOKEN="your_token_here" python bot.py
   ```
   Or copy `.env.example` values into your hosting panel if you deploy it.

3. **Use it**
   - Open your new bot in Telegram, send `/start`, then `/price`

## Hosting options to keep it running 24x7
- Keep it running on a laptop/server with the command above, or
- Deploy free/cheap on Render, Railway, or a small VPS - set `TELEGRAM_BOT_TOKEN` as an environment variable there.
- Without hosting, the bot only replies while `bot.py` is running.

## Honest limits
- Srinagar has no single official published rate. The bot gives the India/international rate as a range basis and tells you to cross-check 2 Srinagar jewellers, IBJA and MCX before buying.
- This is price information and education only, not financial advice and no profit is guaranteed. Buy/sell decisions and amounts are yours.
- Tell Idris your budget, form (coin/bar/jewellery/digital) and holding period, and buy/sell alert levels can be added to the bot.

## Sources
IBJA (ibja.co), MCX (mcxindia.com), RBI USD/INR reference, World Gold Council (gold.org), international spot via goldprice.org, USD/INR via frankfurter.app (ECB reference).
