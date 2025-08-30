from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Iterable, List
import logging

import requests
import json


@dataclass
class TranslatedItem:
    text: str
    detected_source_lang: str | None


class TranslationError(Exception):
    pass


def _preview(text: str, max_len: int = 160) -> str:
    t = text or ""
    if len(t) <= max_len:
        return t
    return t[:max_len] + "…"


class DeepLProvider:
    def __init__(self, api_key: str | None = None, api_url: str | None = None) -> None:
        self.api_key = api_key or os.getenv("DEEPL_API_KEY")
        # free vs pro endpoints; allow override
        self.api_url = api_url or os.getenv("DEEPL_API_URL") or "https://api-free.deepl.com/v2/translate"
        if not self.api_key:
            raise TranslationError("DEEPL_API_KEY is not configured")

    def translate(self, texts: List[str], target_lang: str) -> List[TranslatedItem]:
        # DeepL supports batching via repeated 'text' params
        logging.info("provider=deepl target=%s items=%d sample=%s", target_lang, len(texts), _preview(texts[0] if texts else ""))
        data = [("auth_key", self.api_key), ("target_lang", target_lang.upper())]
        for t in texts:
            data.append(("text", t))
        resp = requests.post(self.api_url, data=data, timeout=30)
        if resp.status_code >= 400:
            raise TranslationError(f"DeepL error: {resp.status_code} {resp.text}")
        js = resp.json()
        out: List[TranslatedItem] = []
        for it in js.get("translations", []):
            out.append(TranslatedItem(text=it.get("text", ""), detected_source_lang=it.get("detected_source_language")))
        if len(out) != len(texts):
            raise TranslationError("DeepL returned unexpected count")
        if out:
            logging.info("provider=deepl output_sample=%s", _preview(out[0].text))
        return out


class MockProvider:
    def translate(self, texts: List[str], target_lang: str) -> List[TranslatedItem]:
        # Simple mock: prefix with target language code; no detection
        return [TranslatedItem(text=f"[{target_lang.upper()}] {t}", detected_source_lang=None) for t in texts]


class LibreProvider:
    def __init__(self, api_url: str | None = None, api_key: str | None = None) -> None:
        # Public demo endpoint; consider self-hosting for production usage
        self.api_url = api_url or os.getenv("LT_API_URL") or "https://libretranslate.com/translate"
        self.api_key = api_key or os.getenv("LT_API_KEY")

    def translate(self, texts: List[str], target_lang: str) -> List[TranslatedItem]:
        payload: dict = {
            "q": texts,
            "source": "auto",
            "target": target_lang.lower(),
            "format": "text",
        }
        if self.api_key:
            payload["api_key"] = self.api_key
        logging.info("provider=libre target=%s items=%d sample=%s", target_lang, len(texts), _preview(texts[0] if texts else ""))
        resp = requests.post(self.api_url, json=payload, timeout=30)
        if resp.status_code >= 400:
            raise TranslationError(f"LibreTranslate error: {resp.status_code} {resp.text}")
        js = resp.json()
        # API returns a list of { translatedText }
        # Some deployments return an object for single-string input; normalize
        out: List[TranslatedItem] = []
        if isinstance(js, list):
            for it in js:
                out.append(TranslatedItem(text=it.get("translatedText", ""), detected_source_lang=None))
        elif isinstance(js, dict) and "translatedText" in js:
            out.append(TranslatedItem(text=js.get("translatedText", ""), detected_source_lang=None))
        else:
            # try to handle shape like { translations: [ { translatedText } ] }
            for it in (js.get("translations", []) if isinstance(js, dict) else []):
                out.append(TranslatedItem(text=it.get("translatedText", ""), detected_source_lang=None))
        if len(out) != len(texts):
            # Best-effort: if single returned for batch, replicate
            if len(out) == 1 and len(texts) > 1:
                out = [out[0]] * len(texts)
            else:
                raise TranslationError("LibreTranslate returned unexpected count")
        if out:
            logging.info("provider=libre output_sample=%s", _preview(out[0].text))
        return out


class MyMemoryProvider:
    def __init__(self, api_url: str | None = None) -> None:
        # Public endpoint without key (rate limited)
        self.api_url = api_url or os.getenv("MM_API_URL") or "https://api.mymemory.translated.net/get"

    def translate(self, texts: List[str], target_lang: str) -> List[TranslatedItem]:
        out: List[TranslatedItem] = []
        for t in texts:
            try:
                # Heuristic source detection: MyMemory does not accept 'auto' for some deployments.
                src = self._guess_source_lang(t)
                logging.info("provider=mymemory src=%s target=%s input=%s", src, target_lang, _preview(t))
                params = {
                    "q": t,
                    "langpair": f"{src}|{target_lang.lower()}",
                }
                resp = requests.get(self.api_url, params=params, timeout=30)
                if resp.status_code >= 400:
                    raise TranslationError(f"MyMemory error: {resp.status_code} {resp.text}")
                js = resp.json()
                txt = ""
                if isinstance(js, dict):
                    data = js.get("responseData", {})
                    txt = data.get("translatedText", "")
                # Guard against instruction-like responses from MyMemory
                if not txt or txt.strip().upper().startswith("PLEASE SELECT TWO DISTINCT LANGUAGES"):
                    txt = t
                out.append(TranslatedItem(text=txt, detected_source_lang=None))
                logging.info("provider=mymemory output=%s", _preview(txt))
            except requests.RequestException as e:
                raise TranslationError(str(e))
        return out

    @staticmethod
    def _guess_source_lang(text: str) -> str:
        # Very light heuristic: detect Cyrillic as Russian/Ukrainian, basic Latin as English
        for ch in text:
            code = ord(ch)
            # Cyrillic block
            if 0x0400 <= code <= 0x04FF:
                # Try to distinguish Ukrainian letters і, ї, є, ґ
                if any(c in text for c in ("і", "ї", "є", "ґ")):
                    return "uk"
                return "ru"
        return "en"


class GeminiProvider:
    def __init__(self, api_key: str | None = None, model_name: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise TranslationError("GEMINI_API_KEY is not configured")
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        # Lazy import to avoid hard dependency unless used
        try:
            import google.generativeai as genai  # type: ignore
        except Exception as e:  # pragma: no cover
            raise TranslationError(f"google-generativeai package not installed: {e}")
        self._genai = genai
        self._genai.configure(api_key=self.api_key)
        self._model = self._genai.GenerativeModel(self.model_name)

    def translate(self, texts: List[str], target_lang: str) -> List[TranslatedItem]:
        # LLM translates one by one to preserve ordering and simplify parsing
        prompt_template = (
            "Translate the following text into {lang}. "
            "Fix typos, preserve meaning, and return ONLY the translated text (no quotes, no extra words).\n\n"
            "Text: \n{source}"
        )
        results: List[TranslatedItem] = []
        for t in texts:
            try:
                prompt = prompt_template.format(lang=target_lang.upper(), source=t)
                logging.info("provider=gemini target=%s input=%s", target_lang, _preview(t))
                resp = self._model.generate_content(prompt)

                # Safe extraction without triggering SDK quick-accessor errors when 0 candidates
                out_text = ""
                try:
                    candidates = getattr(resp, "candidates", None) or []
                    for cand in candidates:
                        content = getattr(cand, "content", None)
                        parts = getattr(content, "parts", None) or []
                        buf: List[str] = []
                        for p in parts:
                            txt = getattr(p, "text", None)
                            if txt:
                                buf.append(txt)
                        if buf:
                            out_text = "".join(buf).strip()
                            if out_text:
                                break
                except Exception:
                    # Ignore parsing issues and try fallback below
                    pass

                if not out_text:
                    try:
                        # May raise when there are 0 candidates; keep in try
                        maybe = getattr(resp, "text", None)
                        if maybe:
                            out_text = str(maybe).strip()
                    except Exception:
                        out_text = ""

                if not out_text:
                    # Most likely safety block or empty answer. Log prompt_feedback for debugging
                    feedback = getattr(resp, "prompt_feedback", None)
                    reason = getattr(feedback, "block_reason", None) or repr(feedback)
                    logging.warning("provider=gemini no_candidates_or_empty reason=%s", reason)
                    out_text = t  # fallback to original text to avoid hard failure

                results.append(TranslatedItem(text=out_text, detected_source_lang=None))
                logging.info("provider=gemini output=%s", _preview(out_text))
            except Exception as e:  # pragma: no cover
                # Do not fail the whole request; log and fallback to original text
                logging.warning("provider=gemini exception=%s -- falling back to original text", e)
                results.append(TranslatedItem(text=t, detected_source_lang=None))
        return results

def translate_texts(texts: List[str], target_lang: str, provider: str | None = None) -> List[TranslatedItem]:
    if not texts:
        return []
    prov = provider or os.getenv("TRANSLATION_PROVIDER")
    if not prov:
        prov = "deepl" if os.getenv("DEEPL_API_KEY") else "mock"
    prov = prov.lower()
    if prov == "deepl":
        client = DeepLProvider()
    elif prov == "libre":
        client = LibreProvider()
    elif prov == "mymemory":
        client = MyMemoryProvider()
    elif prov == "gemini":
        client = GeminiProvider()
    elif prov == "mock":
        client = MockProvider()
    else:
        raise TranslationError(f"Unsupported provider: {prov}")

    # batching with backoff
    batch_size = int(os.getenv("TRANSLATION_BATCH_SIZE", "50"))
    results: List[TranslatedItem] = []
    for i in range(0, len(texts), batch_size):
        chunk = texts[i : i + batch_size]
        attempts = 0
        while True:
            attempts += 1
            try:
                results.extend(client.translate(chunk, target_lang))
                break
            except TranslationError as e:
                if attempts >= 3:
                    raise
                time.sleep(1.5 * attempts)
    return results


