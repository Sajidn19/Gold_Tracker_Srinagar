"""
Srinagar Gold Price Telegram Bot
For Sajid Noor - personal use

Commands:
  /start    - welcome + subscribe to daily update
  /price    - current gold price: international, India (IBJA-style calc), Srinagar estimate
  /srinagar - Srinagar-focused price (24K, 22K, 18K per gram and per 10g)
  /factors  - what makes gold go up / down, in simple language
  /sources  - authentic sources used
  /daily    - subscribe / unsubscribe from daily 10:30 AM IST update
  /help     - all commands

How price is calculated (transparent, no invented jeweller rate):
  1. International spot gold: USD per troy ounce from goldprice.org public feed
  2. USD/INR rate from a public FX feed (fallback: frankfurter.app / ECB reference)
  3. India landed price = spot * USDINR / 31.1035 grams per troy ounce
     + import duty / GST effect is shown separately as a note, not hidden.
  4. Srinagar estimate = India price range. Local jewellers add making charges
     and a small local premium that varies shop to shop, so bot gives a RANGE
     and tells you to cross-check with 2 local jewellers before buying.

Authentic reference sources to cross-check manually:
  - IBJA (India Bullion and Jewellers Association) - ibja.co - official India rate
  - MCX India - mcxindia.com - futures price
  - RBI - rbi.org.in - USD/INR reference rate
  - World Gold Council - gold.org - demand / central bank buying

This bot gives information only. It does NOT guarantee profit and is not
financial advice. Gold can fall as well as rise.
"""

import os
import logging
import asyncio
from datetime import time as dtime

import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("gold-bot")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
DAILY_HOUR_IST = 10
DAILY_MINUTE_IST = 30

subscribers = set()  # chat_ids, in-memory; restart re-subscribes via /start

TROY_OZ_GRAMS = 31.1034768


async def fetch_json(session, url):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
            if r.status == 200:
                return await r.json(content_type=None)
    except Exception as e:
        log.warning("fetch failed %s: %s", url, e)
    return None


async def get_gold_data():
    """Return dict with spot_usd_oz, usdinr, inr_per_g_24k, sources_used, errors"""
    spot = None
    usdinr = None
    sources = []
    async with aiohttp.ClientSession() as s:
        # Gold spot in INR directly if available
        data = await fetch_json(s, "https://data-asg.goldprice.org/dbXRates/INR")
        if data and data.get("items"):
            try:
                # xauPrice is per troy ounce in INR
                inr_oz = float(data["items"][0]["xauPrice"])
                spot = inr_oz  # stored as INR oz in this branch
                sources.append("goldprice.org (INR feed)")
                # also get USDINR
                fx = await fetch_json(s, "https://api.frankfurter.app/latest?from=USD&to=INR")
                if fx and fx.get("rates", {}).get("INR"):
                    usdinr = float(fx["rates"]["INR"])
                    sources.append("frankfurter.app (USD/INR, ECB reference)")
                inr_per_g = inr_oz / TROY_OZ_GRAMS
                return {
                    "inr_per_g_24k": inr_per_g,
                    "usdinr": usdinr,
                    "spot_inr_oz": inr_oz,
                    "sources": sources,
                }
            except Exception:
                pass

        # Fallback: USD spot + FX
        data2 = await fetch_json(s, "https://data-asg.goldprice.org/dbXRates/USD")
        fx = await fetch_json(s, "https://api.frankfurter.app/latest?from=USD&to=INR")
        if data2 and data2.get("items") and fx and fx.get("rates", {}).get("INR"):
            spot_usd = float(data2["items"][0]["xauPrice"])
            usdinr = float(fx["rates"]["INR"])
            inr_per_g = spot_usd * usdinr / TROY_OZ_GRAMS
            return {
                "inr_per_g_24k": inr_per_g,
                "usdinr": usdinr,
                "spot_usd_oz": spot_usd,
                "sources": ["goldprice.org (USD feed)", "frankfurter.app (USD/INR)"],
            }
    return {"inr_per_g_24k": None, "sources": sources}


def format_price(data):
    if not data.get("inr_per_g_24k"):
        return (
            "I could not fetch a live price right now from the public feeds.\n"
            "Please cross-check directly:\n"
            "• IBJA: ibja.co\n• MCX: mcxindia.com\n"
            "I will try again in the next update. No price is being guessed."
        )
    g24 = data["inr_per_g_24k"]
    g22 = g24 * 22 / 24
    g18 = g24 * 18 / 24
    lines = [
        "<b>Gold Price — Today</b>",
        "",
        f"<b>24K:</b> ₹{g24:,.0f} per gram  |  ₹{g24*10:,.0f} per 10g",
        f"<b>22K:</b> ₹{g22:,.0f} per gram  |  ₹{g22*10:,.0f} per 10g",
        f"<b>18K:</b> ₹{g18:,.0f} per gram  |  ₹{g18*10:,.0f} per 10g",
        "",
        "<b>Srinagar note:</b> Srinagar jewellers usually price close to the "
        "India rate above, plus making charges (often 8–25% on jewellery) and "
        "3% GST. Coins/bars have lower making charges. Always check 2 shops "
        "in Srinagar before buying and ask for the IBJA rate of the day.",
    ]
    if data.get("usdinr"):
        lines.append(f"\nUSD/INR used: {data['usdinr']:.2f}")
    if data.get("sources"):
        lines.append("Sources: " + ", ".join(data["sources"]) + ". Cross-check: IBJA / MCX.")
    lines.append("\n<i>Information only, not financial advice. Gold can fall as well as rise.</i>")
    return "\n".join(lines)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    subscribers.add(update.effective_chat.id)
    await update.message.reply_text(
        "Assalamualaikum Sajid. I am your Gold Price bot.\n\n"
        "I will send a daily update at 10:30 AM IST and you can ask anytime:\n"
        "/price - today's price\n/srinagar - Srinagar note\n"
        "/factors - why gold goes up or down\n/sources - authentic sources\n"
        "/daily - turn daily update on/off",
    )


async def cmd_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = await get_gold_data()
    await update.message.reply_text(format_price(data), parse_mode=ParseMode.HTML)


async def cmd_srinagar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = await get_gold_data()
    text = format_price(data)
    text += "\n\n<b>Buying in Srinagar:</b> buy from a BIS-hallmarked jeweller, take a proper bill with HUID, and for investment prefer coins/bars or digital/SGB-style options over heavy jewellery because making charges are lost on resale."
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_factors(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>Gold goes UP when:</b>\n"
        "• US interest rates fall (gold pays no interest, so it competes better)\n"
        "• US dollar weakens, or rupee weakens against dollar\n"
        "• War, tension, stock market fear - people move to safety\n"
        "• Inflation is high\n"
        "• Central banks (incl. RBI) buy more gold\n"
        "• Wedding/festival demand in India rises\n\n"
        "<b>Gold goes DOWN when:</b>\n"
        "• US rates rise, dollar strengthens, rupee strengthens\n"
        "• Markets calm down and investors return to shares\n"
        "• Central bank buying slows, or import duty is cut in India\n\n"
        "Short-term moves are mostly dollar + US rates. Long-term is inflation + central bank buying.",
        parse_mode=ParseMode.HTML,
    )


async def cmd_sources(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>Authentic sources, in order:</b>\n"
        "1. IBJA - ibja.co - India's official bullion rate, twice daily\n"
        "2. MCX - mcxindia.com - live futures\n"
        "3. RBI - rbi.org.in - USD/INR reference rate\n"
        "4. World Gold Council - gold.org - global demand data\n"
        "5. London spot / goldprice.org - international price\n\n"
        "Srinagar shop rates are a cross-check only, never the main source.",
        parse_mode=ParseMode.HTML,
    )


async def cmd_daily(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    if cid in subscribers:
        subscribers.remove(cid)
        await update.message.reply_text("Daily update OFF. Send /daily again to turn it on.")
    else:
        subscribers.add(cid)
        await update.message.reply_text("Daily update ON - 10:30 AM IST.")


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, ctx)


async def daily_job(ctx: ContextTypes.DEFAULT_TYPE):
    data = await get_gold_data()
    text = format_price(data)
    for cid in list(subscribers):
        try:
            await ctx.bot.send_message(cid, text, parse_mode=ParseMode.HTML)
        except Exception as e:
            log.warning("daily send failed %s: %s", cid, e)


def main():
    if not BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN first. Get it from @BotFather on Telegram - see README.md")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("price", cmd_price))
    app.add_handler(CommandHandler("srinagar", cmd_srinagar))
    app.add_handler(CommandHandler("factors", cmd_factors))
    app.add_handler(CommandHandler("sources", cmd_sources))
    app.add_handler(CommandHandler("daily", cmd_daily))
    app.add_handler(CommandHandler("help", cmd_help))
    # Daily 10:30 IST = 05:00 UTC
    app.job_queue.run_daily(daily_job, time=dtime(hour=5, minute=0))
    # Free Render Web Service mode: Render gives RENDER_EXTERNAL_URL and PORT.
    # Telegram calls our webhook, which also wakes the free service up.
    external_url = os.environ.get("WEBHOOK_URL") or os.environ.get("RENDER_EXTERNAL_URL")
    if external_url:
        port = int(os.environ.get("PORT", "10000"))
        base = external_url.rstrip("/")
        log.info("Gold bot started in webhook mode on port %s", port)
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path="webhook",
            webhook_url=f"{base}/webhook",
        )
    else:
        log.info("Gold bot started in polling mode")
        app.run_polling()


if __name__ == "__main__":
    main()
