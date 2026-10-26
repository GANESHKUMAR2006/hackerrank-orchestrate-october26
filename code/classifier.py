"""Deterministic, explainable request intent classifier.

Classifies incoming request texts into:
- DELETE_REQUEST: Request authorizes account or personal data deletion.
- NOT_APPLICABLE: Request is for data access, export, contact update, marketing opt-out, or an inquiry.
- AMBIGUOUS: Request contains conflicting signals or insufficient information to decide safely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import List, Optional, Tuple


class RequestIntent(str, Enum):
    DELETE_REQUEST = "DELETE_REQUEST"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    AMBIGUOUS = "AMBIGUOUS"


class IntentReason(str, Enum):
    EXPLICIT_DELETION = "EXPLICIT_DELETION"
    DATA_ACCESS_OR_EXPORT = "DATA_ACCESS_OR_EXPORT"
    CONTACT_UPDATE_RECTIFICATION = "CONTACT_UPDATE_RECTIFICATION"
    MARKETING_OPTOUT = "MARKETING_OPTOUT"
    ACCOUNT_RETENTION_OVERRIDE = "ACCOUNT_RETENTION_OVERRIDE"
    INQUIRY_ONLY = "INQUIRY_ONLY"
    AMBIGUOUS_CONFLICTING = "AMBIGUOUS_CONFLICTING"
    AMBIGUOUS_NO_SIGNAL = "AMBIGUOUS_NO_SIGNAL"


@dataclass
class IntentClassification:
    """Detailed result of intent classification."""
    intent: RequestIntent
    confidence: float
    reason_code: IntentReason
    original_text: str
    matched_signals: List[str] = field(default_factory=list)
    explanation: str = ""


class RequestIntentClassifier:
    """Multilingual intent classifier supporting English, French, Spanish, and Japanese."""

    # 1. Explicit retention / non-deletion override patterns (highest priority)
    RETENTION_OVERRIDE_PATTERNS = [
        # English
        r"\bleave\s+(?:the\s+account|my\s+profile|everything)\s+active\b",
        r"\bleave\s+(?:my\s+profile|the\s+account|my\s+purchase\s+history)\s+in\s+place\b",
        r"\bkeep\s+the\s+account\b",
        r"\bdo\s+not\s+(?:close|delete|remove|erase)\b",
        r"\bdon't\s+(?:close|delete|remove|erase)\b",
        r"\bnot\s+asking\s+for\s+deletion\b",
        r"\bnot\s+a\s+request\s+to\s+erase\b",
        r"\bwant\s+to\s+continue\s+using\s+the\s+service\b",
        r"\bplease\s+keep\s+(?:the\s+account|my\s+account)\b",
        r"\bwithout\s+removing\s+any\s+of\s+my\s+records\b",
        # French
        r"\bgarder\s+le\s+compte\b",
        r"\blaisser\s+le\s+compte\s+actif\b",
        r"\bne\s+pas\s+(?:supprimer|fermer|effacer)\b",
        r"\bpas\s+une\s+demande\s+de\s+suppression\b",
        # Spanish
        r"\bmantener\s+la\s+cuenta\b",
        r"\bdejar\s+la\s+cuenta\s+activa\b",
        r"\bno\s+(?:eliminar|borrar|cerrar)\b",
        r"\bno\s+es\s+una\s+solicitud\s+de\s+eliminaci[oó]n\b",
        # Japanese
        r"アカウント(?:は|を)残して",
        r"削除(?:しないで|させないで)",
        r"利用を続(?:けたい|けます)",
    ]

    # 2. Marketing opt-out signals
    MARKETING_OPTOUT_PATTERNS = [
        r"\bstop\s+(?:the\s+)?promotional\b",
        r"\bmarketing\s+lists?\s+only\b",
        r"\bunsubscribe\b",
        r"\bopt\s+out\s+of\s+marketing\b",
        r"\bd[eé]sabonner\b",
        r"\bcorreos\s+promocionales\b",
        r"\bbaja\s+de\s+marketing\b",
        r"配信停止",
        r"メルマガ解除",
    ]

    # 3. Contact update / Rectification signals
    RECTIFICATION_PATTERNS = [
        r"\bmobile\s+number\b.*?\bout\s+of\s+date\b",
        r"\breplace\s+it\s+with\s+the\s+new\s+one\b",
        r"\bchange\s+the\s+email\s+address\b.*?\bcontinue\b",
        r"\bsurname\s+is\s+misspelled\b",
        r"\bcorrect\s+(?:it|my\s+name|my\s+details)\b",
        r"\bupdate\s+my\s+(?:phone|address|email|details)\b",
        r"\bmettre\s+[àa]\s+jour\b",
        r"\bactualizar\s+mi\b",
        r"\bcorregir\s+mi\b",
        r"更新して",
        r"変更して",
        r"修正して",
    ]

    # 4. Data access / Portability / Export requests
    ACCESS_EXPORT_PATTERNS = [
        r"\bdownload\s+my\s+account\s+information\b",
        r"\bportable\s+format\b",
        r"\bsend\s+me\s+a\s+copy\b",
        r"\bcopy\s+of\s+(?:last\s+year's\s+invoices|my\s+records|the\s+information)\b",
        r"\bwhat\s+personal\s+information\s+you\s+hold\b",
        r"\binformation\s+request\b",
        r"\bcan't\s+access\s+my\s+profile\b",
        r"\bresetting\s+the\s+login\b",
        r"\bt[ée]l[ée]charger\s+mes\s+donn[ée]es\b",
        r"\bcopie\s+de\s+mes\s+donn[ée]es\b",
        r"\bdescargar\s+mis\s+datos\b",
        r"\bcopia\s+de\s+mis\s+datos\b",
        r"データをダウンロード",
        r"情報のコピー",
        r"アクセスできない",
    ]

    # 5. Pure inquiries / questions without deletion authorization
    INQUIRY_PATTERNS = [
        r"^[¿\s]*how\s+(?:do|can)\s+i\s+(?:delete|close|erase)\b.*?\?",
        r"^[¿\s]*what\s+happens\s+if\s+i\s+(?:delete|close|erase)\b.*?\?",
        r"^[¿\s]*comment\s+puis-je\s+(?:supprimer|fermer)\b.*?\?",
        r"^[¿\s]*c[oó]mo\s+puedo\s+(?:eliminar|borrar|cerrar)\b.*?\?",
        r"どうやって削除.*?ですか[？\?]",
    ]

    # 6. Positive deletion intent patterns
    DELETION_PATTERNS = [
        # English
        r"\b(?:please\s+)?(?:permanently\s+)?delete\s+(?:my|this|the)\s+account\b",
        r"\baccount[- ]deletion\s+request\b",
        r"\bpermanent\s+account[- ]deletion\b",
        r"\bclose\s+(?:this|my|the)\s+account\b",
        r"\bwould\s+like\s+it\s+closed\b",
        r"\bwant\s+it\s+closed\b",
        r"\berased?\b",
        r"\berase\s+the\s+account\b",
        r"\brequesting\s+deletion\b",
        r"\bremove\s+(?:my\s+account|this\s+account|the\s+account|my\s+profile|the\s+profile|records|that\s+search\s+result|my\s+name|the\s+rest)\b",
        r"\bdeletion\s+process\b",
        r"\bdeleted\s+(?:this|my)\s+account\b",
        r"\bdeleting\s+(?:my|this|it)\b",
        r"\bpersonal[- ]data\s+deletion\b",
        r"\bclosed\s+(?:my|this)\s+account\b",
        r"\baccount\s+(?:was|had\s+been)\s+deleted\b",
        r"\baccount\s+(?:page\s+is|itself\s+is)\s+gone\b",
        r"\bfinish\s+(?:the\s+)?deletion\b",
        r"\baudit\s+(?:the\s+)?deletion\b",
        r"\bverify\s+that\s+(?:my\s+account\s+was\s+deleted|the\s+profile\s+is\s+gone)\b",
        r"\bno\s+longer\s+need\s+this\s+account\b",
        r"\bconfirm\s+that\s+the\s+profile\s+is\s+gone\b",
        r"\bremoved\b.*?\baccount\b",
        r"\baccount\b.*?\bremoved\b",
        # French
        r"\bsuppression\s+d[ée]finitive\b",
        r"\bsupprimer\s+(?:mon|ce|le)\s+compte\b",
        r"\beffacer\s+(?:mon|ce|le)\s+compte\b",
        r"\bdemande\s+de\s+suppression\b",
        r"\bcl[oô]turer\s+(?:mon|ce)\s+compte\b",
        # Spanish
        r"\beliminar\s+(?:mi|esta|la)\s+cuenta\b",
        r"\beliminaci[oó]n\s+definitiva\b",
        r"\bborrar\s+(?:mi|esta|la)\s+cuenta\b",
        r"\bcancelar\s+mi\s+cuenta\b",
        r"\bcerrar\s+mi\s+cuenta\b",
        r"\bsolicitud\s+de\s+eliminaci[oó]n\b",
        r"\bintent[eé]\s+eliminar\s+mi\s+cuenta\b",
        # Japanese
        r"アカウントの(?:完全な)?削除",
        r"アカウントを消去",
        r"アカウントを閉じる",
        r"アカウントの削除を依頼",
        r"削除手続き",
    ]

    def classify(self, request_text: str) -> IntentClassification:
        """Classify request text into DELETE_REQUEST, NOT_APPLICABLE, or AMBIGUOUS."""
        text = (request_text or "").strip()
        if not text:
            return IntentClassification(
                intent=RequestIntent.AMBIGUOUS,
                confidence=0.0,
                reason_code=IntentReason.AMBIGUOUS_NO_SIGNAL,
                original_text=text,
                matched_signals=[],
                explanation="Request text is empty or blank.",
            )

        lower_text = text.lower()

        # Check 1: Explicit retention override (highest priority)
        matched_override = self._find_matches(self.RETENTION_OVERRIDE_PATTERNS, lower_text)
        if matched_override:
            return IntentClassification(
                intent=RequestIntent.NOT_APPLICABLE,
                confidence=0.98,
                reason_code=IntentReason.ACCOUNT_RETENTION_OVERRIDE,
                original_text=text,
                matched_signals=matched_override,
                explanation="User explicitly requested to keep account active or not delete.",
            )

        # Check 2: Marketing opt-out only
        matched_marketing = self._find_matches(self.MARKETING_OPTOUT_PATTERNS, lower_text)
        if matched_marketing and not self._has_strong_deletion_command(lower_text):
            return IntentClassification(
                intent=RequestIntent.NOT_APPLICABLE,
                confidence=0.95,
                reason_code=IntentReason.MARKETING_OPTOUT,
                original_text=text,
                matched_signals=matched_marketing,
                explanation="Request is for marketing email opt-out only.",
            )

        # Check 3: Rectification / Contact update only
        matched_rectification = self._find_matches(self.RECTIFICATION_PATTERNS, lower_text)
        if matched_rectification and not self._has_strong_deletion_command(lower_text):
            return IntentClassification(
                intent=RequestIntent.NOT_APPLICABLE,
                confidence=0.95,
                reason_code=IntentReason.CONTACT_UPDATE_RECTIFICATION,
                original_text=text,
                matched_signals=matched_rectification,
                explanation="Request is to update or correct contact details without deletion.",
            )

        # Check 4: Access or Export request
        matched_access = self._find_matches(self.ACCESS_EXPORT_PATTERNS, lower_text)
        if matched_access and not self._has_strong_deletion_command(lower_text):
            return IntentClassification(
                intent=RequestIntent.NOT_APPLICABLE,
                confidence=0.95,
                reason_code=IntentReason.DATA_ACCESS_OR_EXPORT,
                original_text=text,
                matched_signals=matched_access,
                explanation="Request is for data export, copy, or login access.",
            )

        # Check 5: Pure inquiry / question without command
        matched_inquiry = self._find_matches(self.INQUIRY_PATTERNS, lower_text)
        if matched_inquiry:
            return IntentClassification(
                intent=RequestIntent.NOT_APPLICABLE,
                confidence=0.90,
                reason_code=IntentReason.INQUIRY_ONLY,
                original_text=text,
                matched_signals=matched_inquiry,
                explanation="Text is an informational question rather than authorization to delete.",
            )

        # Check 6: Positive deletion intent
        matched_deletion = self._find_matches(self.DELETION_PATTERNS, lower_text)
        if matched_deletion:
            return IntentClassification(
                intent=RequestIntent.DELETE_REQUEST,
                confidence=0.95,
                reason_code=IntentReason.EXPLICIT_DELETION,
                original_text=text,
                matched_signals=matched_deletion,
                explanation="User authorized deletion of account and/or personal data.",
            )

        # Check 7: Fallback ambiguous check
        # If text has question marks or non-deletion signals mixed with unrecognized phrases
        if "?" in text or any(term in lower_text for term in ["help", "info", "query", "question"]):
            return IntentClassification(
                intent=RequestIntent.AMBIGUOUS,
                confidence=0.50,
                reason_code=IntentReason.AMBIGUOUS_CONFLICTING,
                original_text=text,
                matched_signals=[],
                explanation="Request contains ambiguous or conflicting language.",
            )

        return IntentClassification(
            intent=RequestIntent.AMBIGUOUS,
            confidence=0.30,
            reason_code=IntentReason.AMBIGUOUS_NO_SIGNAL,
            original_text=text,
            matched_signals=[],
            explanation="No recognized deletion or non-deletion intent signals found.",
        )

    def _find_matches(self, patterns: List[str], text: str) -> List[str]:
        matches: List[str] = []
        for p in patterns:
            found = re.findall(p, text, re.IGNORECASE)
            if found:
                matches.append(p)
        return matches

    def _has_strong_deletion_command(self, text: str) -> bool:
        """Return True if text contains an explicit deletion command despite other mentions."""
        strong_commands = [
            r"\bpermanently\s+delete\b",
            r"\bdelete\s+(?:this|my)\s+account\b",
            r"\bsupprimer\s+(?:mon|ce)\s+compte\b",
            r"\beliminar\s+(?:mi|esta)\s+cuenta\b",
            r"アカウントの完全な削除",
        ]
        return bool(self._find_matches(strong_commands, text))
