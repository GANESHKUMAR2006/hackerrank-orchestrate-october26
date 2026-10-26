"""Unit tests for RequestIntentClassifier across languages and intents."""

import pytest

from code.classifier import (
    IntentReason,
    RequestIntent,
    RequestIntentClassifier,
)


@pytest.fixture
def classifier():
    return RequestIntentClassifier()


# --- 1. Multilingual Deletion Requests ---

def test_english_deletion_requests(classifier):
    texts = [
        "Please delete my account and the personal details attached to it.",
        "I am requesting permanent account deletion for this email address.",
        "I want to close this account and have its associated personal data deleted.",
        "I would like the account associated with this address to be erased.",
    ]
    for text in texts:
        res = classifier.classify(text)
        assert res.intent == RequestIntent.DELETE_REQUEST, f"Failed for: {text}"
        assert res.reason_code == IntentReason.EXPLICIT_DELETION
        assert res.confidence >= 0.90


def test_french_deletion_requests(classifier):
    texts = [
        "Je demande la suppression définitive du compte associé à cette adresse e-mail.",
        "Veuillez supprimer mon compte et effacer mes données personnelles.",
    ]
    for text in texts:
        res = classifier.classify(text)
        assert res.intent == RequestIntent.DELETE_REQUEST, f"Failed for: {text}"
        assert res.reason_code == IntentReason.EXPLICIT_DELETION


def test_spanish_deletion_requests(classifier):
    texts = [
        "Intenté eliminar mi cuenta ayer, por favor completar la eliminación.",
        "Por favor procesar la eliminación definitiva de mi cuenta.",
        "Solicito borrar mi cuenta y cancelar todos mis datos asociados.",
    ]
    for text in texts:
        res = classifier.classify(text)
        assert res.intent == RequestIntent.DELETE_REQUEST, f"Failed for: {text}"
        assert res.reason_code == IntentReason.EXPLICIT_DELETION


def test_japanese_deletion_requests(classifier):
    texts = [
        "このメールアドレスに関連するアカウントの完全な削除を依頼します。",
        "アカウントの削除手続きをお願いします。",
    ]
    for text in texts:
        res = classifier.classify(text)
        assert res.intent == RequestIntent.DELETE_REQUEST, f"Failed for: {text}"
        assert res.reason_code == IntentReason.EXPLICIT_DELETION


# --- 2. Non-Deletion Intents ---

def test_data_access_and_export_requests(classifier):
    texts = [
        "I'd like to download my account information in a portable format. Please keep the account as it is.",
        "Can you tell me what personal information you hold about me? This is an information request, not a request to erase it.",
        "Could you send me a copy of the information held on my account? I still use it, so please don't delete or change anything.",
        "I need a copy of last year's invoices for my records. Please leave my profile and purchase history in place.",
    ]
    for text in texts:
        res = classifier.classify(text)
        assert res.intent == RequestIntent.NOT_APPLICABLE, f"Failed for: {text}"
        assert res.reason_code in {IntentReason.DATA_ACCESS_OR_EXPORT, IntentReason.ACCOUNT_RETENTION_OVERRIDE}


def test_contact_update_and_rectification_requests(classifier):
    texts = [
        "The mobile number on my profile is out of date. Please replace it with the new one and leave the account active.",
        "My surname is misspelled on the account. Can you correct it without removing any of my records?",
        "Please change the email address used for this account. I want to continue using the service.",
    ]
    for text in texts:
        res = classifier.classify(text)
        assert res.intent == RequestIntent.NOT_APPLICABLE, f"Failed for: {text}"
        assert res.reason_code in {IntentReason.CONTACT_UPDATE_RECTIFICATION, IntentReason.ACCOUNT_RETENTION_OVERRIDE}


def test_marketing_opt_out_requests(classifier):
    texts = [
        "Please stop the promotional emails. I still need the account and my order history, so I am not asking for deletion.",
        "Please remove me from marketing lists only. I still want receipts and service messages for this account.",
    ]
    for text in texts:
        res = classifier.classify(text)
        assert res.intent == RequestIntent.NOT_APPLICABLE, f"Failed for: {text}"
        assert res.reason_code in {IntentReason.MARKETING_OPTOUT, IntentReason.ACCOUNT_RETENTION_OVERRIDE}


def test_questions_about_deletion(classifier):
    texts = [
        "How do I delete my account if I choose to in the future?",
        "What happens if I delete my account?",
        "Comment puis-je supprimer mon compte?",
        "¿Cómo puedo eliminar mi cuenta más adelante?",
    ]
    for text in texts:
        res = classifier.classify(text)
        assert res.intent == RequestIntent.NOT_APPLICABLE, f"Failed for: {text}"
        assert res.reason_code == IntentReason.INQUIRY_ONLY


# --- 3. Ambiguous and Edge Cases ---

def test_ambiguous_and_empty_requests(classifier):
    # Blank / empty text
    res_empty = classifier.classify("")
    assert res_empty.intent == RequestIntent.AMBIGUOUS
    assert res_empty.reason_code == IntentReason.AMBIGUOUS_NO_SIGNAL

    # Ambiguous question / vague inquiry
    res_vague = classifier.classify("Can you help me with an account inquiry or question?")
    assert res_vague.intent == RequestIntent.AMBIGUOUS
    assert res_vague.reason_code == IntentReason.AMBIGUOUS_CONFLICTING
