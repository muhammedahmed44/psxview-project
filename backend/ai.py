"""AI explanation of a valuation via Gemini REST. Falls back to plain text if AI fails."""
import logging
import time

import httpx

import config

# Logger for this module, labeled so backend logs show "psxviewai.ai".
log = logging.getLogger("psxviewai.ai")

# Gemini API endpoint. {model} is filled in at call time from config.GEMINI_MODEL.
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def build_prompt(inp: dict, res: dict) -> str:
    """
    Create the prompt sent to Gemini.

    inp: the valuation inputs (symbol, eps, price, years, growth_pct, terminal_pct).
    res: the computed results (required_return_pct, implied_growth_pct, fair_value, upside_pct).
    """
    # implied_growth_pct can be None when the math needs >500% growth.
    implied = res["implied_growth_pct"]
    implied_txt = "more than 500%" if implied is None else f"{implied:.1f}%"

    # Strict instructions keep the AI from giving financial advice or inventing numbers.
    return (
        "You are a careful teaching assistant for retail investors on the Pakistan Stock Exchange.\n"
        "Explain the valuation below in at most 120 words, plain English, no jargon without a short definition.\n"
        "Rules: use ONLY the numbers given. Do NOT say buy, sell or hold. Do NOT predict prices. "
        "Mention one limitation of this method. Finish with: 'Educational only, not advice.'\n\n"
        f"Company: {inp['symbol']}\n"
        f"EPS/FCF per share: Rs {inp['eps']}\nCurrent price: Rs {inp['price']}\n"
        f"Required return (CAPM): {res['required_return_pct']:.1f}%\n"
        f"Projection years: {inp['years']}\n"
        f"Growth the market price already implies: {implied_txt} per year\n"
        f"User's growth estimate: {inp['growth_pct']}% per year, terminal growth {inp['terminal_pct']}%\n"
        f"Fair value at user's estimate: Rs {res['fair_value']:.0f} ({res['upside_pct']:+.0f}% vs price)\n"
    )


def fallback_text(inp: dict, res: dict) -> str:
    """
    Generate a short human-readable summary when Gemini is unavailable.

    This is used both when no API key is configured and after retries fail.
    """
    implied = res["implied_growth_pct"]

    # First sentence describes the implied growth the current price expects.
    a = ("The price needs more than 500% yearly growth to make sense." if implied is None
         else f"The current price already assumes about {implied:.1f}% yearly growth.")

    # Second sentence shows the user's estimate result and how it compares to price.
    b = (f"At your {inp['growth_pct']}% estimate, fair value is Rs {res['fair_value']:.0f}, "
         f"which is {abs(res['upside_pct']):.0f}% {'above' if res['upside_pct'] >= 0 else 'below'} the price.")

    return f"{a} {b} Educational only, not advice."


def generate_text(
    prompt: str,
    fallback: str,
    *,
    max_output_tokens: int = 1200,
    temperature: float = 0.2,
    purpose: str = "text generation",
) -> dict:
    """Generate grounded text with Gemini, returning ``fallback`` on failure."""
    # No API key configured: skip the network call entirely.
    if not config.GEMINI_API_KEY:
        return {"text": fallback, "source": "fallback"}

    # Remember the last error so we can log why we fell back.
    last_error: Exception | None = None

    # Retry up to 3 times for transient failures (network, 429 rate limit, 5xx).
    for attempt in range(3):
        try:
            # Call the Gemini generateContent endpoint.
            r = httpx.post(
                URL.format(model=config.GEMINI_MODEL),
                headers={"x-goog-api-key": config.GEMINI_API_KEY, "Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "maxOutputTokens": max_output_tokens,
                        "temperature": temperature,
                        "thinkingConfig": {"thinkingLevel": "low"},
                    },
                },
                timeout=30,
            )
            r.raise_for_status()

            # Join all text parts because thinking-capable models can return
            # the final answer in more than one part.
            candidate = r.json()["candidates"][0]
            parts = candidate.get("content", {}).get("parts", [])
            text = "".join(str(part.get("text", "")) for part in parts).strip()

            # Guard against empty or blocked responses.
            if not text:
                raise ValueError(f"Gemini returned no text ({candidate.get('finishReason', 'unknown')})")

            return {"text": text, "source": "gemini"}

        except httpx.HTTPStatusError as e:
            # HTTP error from Gemini (e.g., 429 rate limit, 5xx outage, 400 bad request).
            last_error = e
            status = e.response.status_code
            log.warning(
                "Gemini %s failed with HTTP %s (attempt %s/3)",
                purpose,
                status,
                attempt + 1,
            )

            # Do not retry client errors that won't fix themselves (4xx except 429).
            if status != 429 and status < 500:
                break

        except Exception as e:
            # Network errors, JSON parsing errors, unexpected response shapes, etc.
            last_error = e
            log.warning(
                "Gemini %s failed: %s (attempt %s/3)",
                purpose,
                type(e).__name__,
                attempt + 1,
            )

        # Wait before retrying: 1s, then 2s.
        if attempt < 2:
            time.sleep(attempt + 1)

    # All retries exhausted or non-retryable error: return the local fallback text.
    log.warning("Using %s fallback after Gemini failure: %s", purpose, type(last_error).__name__)
    return {"text": fallback, "source": "fallback"}


def explain(inp: dict, res: dict) -> dict:
    """
    Ask Gemini to explain the valuation.

    Returns a dict like {"text": "...", "source": "gemini"} on success,
    or {"text": "...", "source": "fallback"} if Gemini fails or is not configured.
    """
    return generate_text(
        build_prompt(inp, res),
        fallback_text(inp, res),
        max_output_tokens=1200,
        temperature=0.2,
        purpose="valuation explanation",
    )
