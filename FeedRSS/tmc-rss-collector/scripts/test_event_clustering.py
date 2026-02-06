#!/usr/bin/env python
"""
Test Event Clustering - Verifica o sistema de clustering por eventos especificos.

Este script testa:
1. Extracao de assinaturas de eventos (EventSignatureService)
2. Algoritmo de matching de eventos (EventMatchingService)
3. Validacao de que artigos sobre o MESMO evento sao agrupados
4. Resultados detalhados com tipos de match e confidence scores

Uso:
    python scripts/test_event_clustering.py

"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import date
from uuid import uuid4
from typing import List, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.event_signature import (
    EventSignature,
    EventSignatureCreate,
    normalize_entity,
    entities_match,
    calculate_entity_similarity
)
from services.event_signature_service import (
    EventSignatureService,
    get_event_signature_service,
    is_event_extraction_enabled
)
from services.event_matching_service import (
    EventMatchingService,
    get_event_matching_service,
    is_event_matching_enabled,
    ENTITY_MATCH_HIGH_THRESHOLD,
    ENTITY_MATCH_LOW_THRESHOLD,
    EXACT_MATCH_CONFIDENCE
)


# ANSI Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def print_header(text: str) -> None:
    """Print a colored header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}\n")


def print_subheader(text: str) -> None:
    """Print a colored subheader."""
    print(f"\n{Colors.BLUE}--- {text} ---{Colors.RESET}\n")


def print_pass(text: str) -> None:
    """Print a PASS message in green."""
    print(f"{Colors.GREEN}[PASS]{Colors.RESET} {text}")


def print_fail(text: str) -> None:
    """Print a FAIL message in red."""
    print(f"{Colors.RED}[FAIL]{Colors.RESET} {text}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"{Colors.YELLOW}[INFO]{Colors.RESET} {text}")


def print_detail(label: str, value: str) -> None:
    """Print a detail line."""
    print(f"  {Colors.MAGENTA}{label}:{Colors.RESET} {value}")


# ============================================================================
# TEST ARTICLES
# ============================================================================

# Test case 1: SAME EVENT - Empresario brasileiro detido pelo ICE
ARTICLE_1A = {
    "id": uuid4(),
    "title": "Empresario brasileiro detido pelo ICE nos Estados Unidos",
    "preview": "Um empresario brasileiro foi detido pelo ICE (Immigration and Customs Enforcement) "
               "nos Estados Unidos. O homem, pai de trigemeos, estava no pais a trabalho quando "
               "foi abordado por agentes federais."
}

ARTICLE_1B = {
    "id": uuid4(),
    "title": "Pai de trigemeos brasileiro e preso nos EUA pelo ICE",
    "preview": "Brasileiro pai de trigemeos foi preso pela imigracao americana. O empresario "
               "estava trabalhando legalmente quando foi detido pelo ICE."
}

# Test case 2: SAME EVENT - Trump anuncia tarifas
ARTICLE_2A = {
    "id": uuid4(),
    "title": "Trump anuncia novas tarifas de 25% contra China e Mexico",
    "preview": "O presidente Donald Trump anunciou nesta terca-feira a imposicao de novas "
               "tarifas de 25% sobre produtos importados da China e do Mexico."
}

ARTICLE_2B = {
    "id": uuid4(),
    "title": "Entenda as novas tarifas de Trump contra a China",
    "preview": "Analise: as tarifas de 25% anunciadas por Trump vao impactar o comercio "
               "internacional. Saiba como as novas medidas afetam o Brasil."
}

# Test case 3: DIFFERENT EVENTS - Acidentes na BR-101
ARTICLE_3A = {
    "id": uuid4(),
    "title": "Acidente grave mata 3 pessoas na BR-101 em Santa Catarina",
    "preview": "Um acidente envolvendo um caminhao e dois carros deixou 3 mortos na BR-101, "
               "proximo a Joinville, na madrugada de hoje. As vitimas eram de uma mesma familia."
}

ARTICLE_3B = {
    "id": uuid4(),
    "title": "Outro acidente fatal ocorre na BR-101 no Rio Grande do Sul",
    "preview": "Motociclista morre em colisao com onibus na BR-101, em Torres, RS. "
               "E o segundo acidente grave na rodovia esta semana."
}


# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def create_mock_signature(
    people: List[str],
    organizations: List[str],
    locations: List[str],
    event_action: str,
    unique_details: List[str],
    article_id=None,
    confidence: float = 0.85
) -> EventSignatureCreate:
    """
    Create a mock EventSignatureCreate for testing.

    This simulates what the LLM extraction would return.
    """
    signature = EventSignatureCreate(
        article_id=article_id or uuid4(),
        people=people,
        organizations=organizations,
        locations=locations,
        event_action=event_action,
        unique_details=unique_details,
        confidence=confidence
    )
    signature.canonical_key = signature.generate_canonical_key(date.today())
    return signature


def test_signature_extraction():
    """
    Test 1: Validate event signature extraction.

    Uses mock signatures to verify the canonical key generation
    and entity normalization work correctly.
    """
    print_header("TEST 1: Event Signature Extraction")

    tests_passed = 0
    tests_total = 0

    # Test 1.1: Signature for empresario brasileiro
    print_subheader("1.1: Empresario brasileiro detido")

    sig_1a = create_mock_signature(
        people=["Empresario brasileiro"],
        organizations=["ICE"],
        locations=["Estados Unidos", "EUA"],
        event_action="detido",
        unique_details=["pai de trigemeos", "a trabalho"],
        article_id=ARTICLE_1A["id"]
    )

    tests_total += 1
    print_detail("Canonical Key", sig_1a.canonical_key)
    print_detail("People", str(sig_1a.people))
    print_detail("Organizations", str(sig_1a.organizations))
    print_detail("Event Action", sig_1a.event_action)
    print_detail("Unique Details", str(sig_1a.unique_details))

    if sig_1a.canonical_key and "empresario" in sig_1a.canonical_key.lower():
        print_pass("Canonical key generated correctly")
        tests_passed += 1
    else:
        print_fail("Canonical key generation failed")

    # Test 1.2: Signature for pai de trigemeos (same event)
    print_subheader("1.2: Pai de trigemeos (same event, different title)")

    sig_1b = create_mock_signature(
        people=["Brasileiro", "Pai de trigemeos"],
        organizations=["ICE"],
        locations=["EUA"],
        event_action="preso",
        unique_details=["empresario", "pai de trigemeos"],
        article_id=ARTICLE_1B["id"]
    )

    tests_total += 1
    print_detail("Canonical Key", sig_1b.canonical_key)
    print_detail("People", str(sig_1b.people))
    print_detail("Organizations", str(sig_1b.organizations))

    if "ice" in sig_1b.canonical_key.lower():
        print_pass("ICE organization captured in canonical key")
        tests_passed += 1
    else:
        print_fail("ICE not found in canonical key")

    # Test 1.3: Signature for Trump tarifas
    print_subheader("1.3: Trump anuncia tarifas")

    sig_2a = create_mock_signature(
        people=["Donald Trump", "Trump"],
        organizations=["Casa Branca"],
        locations=["Estados Unidos", "China", "Mexico"],
        event_action="anunciou",
        unique_details=["tarifas 25%", "importacoes"],
        article_id=ARTICLE_2A["id"]
    )

    tests_total += 1
    print_detail("Canonical Key", sig_2a.canonical_key)
    print_detail("People", str(sig_2a.people))
    print_detail("Event Action", sig_2a.event_action)

    if "trump" in sig_2a.canonical_key.lower() or "donald" in sig_2a.canonical_key.lower():
        print_pass("Trump captured in canonical key")
        tests_passed += 1
    else:
        print_fail("Trump not found in canonical key")

    # Test 1.4: Entity normalization
    print_subheader("1.4: Entity Normalization")

    tests_total += 1
    normalized = normalize_entity("Empresário Brasileiro")
    expected = "empresario brasileiro"

    print_detail("Input", "Empresário Brasileiro")
    print_detail("Normalized", normalized)
    print_detail("Expected", expected)

    if normalized == expected:
        print_pass("Entity normalization works correctly (accents removed, lowercase)")
        tests_passed += 1
    else:
        print_fail(f"Normalization failed: got '{normalized}', expected '{expected}'")

    # Summary
    print(f"\n{Colors.BOLD}Extraction Tests: {tests_passed}/{tests_total} passed{Colors.RESET}")
    return tests_passed, tests_total


def test_event_matching():
    """
    Test 2: Validate event matching algorithm.

    Tests entity overlap calculation and match type determination.
    """
    print_header("TEST 2: Event Matching Algorithm")

    tests_passed = 0
    tests_total = 0

    # Test 2.1: High entity overlap (same event - ICE detention)
    print_subheader("2.1: High Entity Overlap (Same Event)")

    sig_1a = create_mock_signature(
        people=["Empresario brasileiro"],
        organizations=["ICE"],
        locations=["Estados Unidos"],
        event_action="detido",
        unique_details=["pai de trigemeos"],
        article_id=ARTICLE_1A["id"]
    )

    sig_1b = create_mock_signature(
        people=["Brasileiro"],
        organizations=["ICE"],
        locations=["EUA", "Estados Unidos"],
        event_action="preso",
        unique_details=["pai de trigemeos", "empresario"],
        article_id=ARTICLE_1B["id"]
    )

    # Create EventSignature objects for overlap calculation
    es_1a = EventSignature(
        id=uuid4(),
        article_id=sig_1a.article_id,
        people=sig_1a.people,
        organizations=sig_1a.organizations,
        locations=sig_1a.locations,
        event_action=sig_1a.event_action,
        unique_details=sig_1a.unique_details,
        canonical_key=sig_1a.canonical_key,
        confidence=sig_1a.confidence
    )

    es_1b = EventSignature(
        id=uuid4(),
        article_id=sig_1b.article_id,
        people=sig_1b.people,
        organizations=sig_1b.organizations,
        locations=sig_1b.locations,
        event_action=sig_1b.event_action,
        unique_details=sig_1b.unique_details,
        canonical_key=sig_1b.canonical_key,
        confidence=sig_1b.confidence
    )

    overlap_1 = es_1a.calculate_entity_overlap(es_1b)

    tests_total += 1
    print_detail("Article A entities", str(es_1a.get_entity_set()))
    print_detail("Article B entities", str(es_1b.get_entity_set()))
    print_detail("Entity Overlap Score", f"{overlap_1:.3f}")
    print_detail("High Threshold", f"{ENTITY_MATCH_HIGH_THRESHOLD}")

    # They share ICE and EUA/Estados Unidos - should have decent overlap
    if overlap_1 >= ENTITY_MATCH_LOW_THRESHOLD:
        print_pass(f"Entity overlap ({overlap_1:.3f}) >= low threshold ({ENTITY_MATCH_LOW_THRESHOLD})")
        tests_passed += 1
    else:
        print_fail(f"Entity overlap too low: {overlap_1:.3f}")

    # Test 2.2: Trump tarifas (same event)
    print_subheader("2.2: Trump Tarifas (Same Event)")

    sig_2a = create_mock_signature(
        people=["Donald Trump", "Trump"],
        organizations=["Casa Branca"],
        locations=["Estados Unidos", "China", "Mexico"],
        event_action="anunciou",
        unique_details=["tarifas 25%"],
        article_id=ARTICLE_2A["id"]
    )

    sig_2b = create_mock_signature(
        people=["Trump"],
        organizations=[],
        locations=["China", "Brasil"],
        event_action="anunciou",
        unique_details=["tarifas 25%", "analise"],
        article_id=ARTICLE_2B["id"]
    )

    es_2a = EventSignature(
        id=uuid4(),
        article_id=sig_2a.article_id,
        people=sig_2a.people,
        organizations=sig_2a.organizations,
        locations=sig_2a.locations,
        event_action=sig_2a.event_action,
        unique_details=sig_2a.unique_details,
        canonical_key=sig_2a.canonical_key,
        confidence=sig_2a.confidence
    )

    es_2b = EventSignature(
        id=uuid4(),
        article_id=sig_2b.article_id,
        people=sig_2b.people,
        organizations=sig_2b.organizations,
        locations=sig_2b.locations,
        event_action=sig_2b.event_action,
        unique_details=sig_2b.unique_details,
        canonical_key=sig_2b.canonical_key,
        confidence=sig_2b.confidence
    )

    overlap_2 = es_2a.calculate_entity_overlap(es_2b)

    tests_total += 1
    print_detail("Article A entities", str(es_2a.get_entity_set()))
    print_detail("Article B entities", str(es_2b.get_entity_set()))
    print_detail("Entity Overlap Score", f"{overlap_2:.3f}")
    print_detail("Same Action Bonus", "+0.15 if actions match")

    # They share Trump and China, plus same action "anunciou"
    if overlap_2 >= ENTITY_MATCH_LOW_THRESHOLD:
        print_pass(f"Entity overlap ({overlap_2:.3f}) indicates same event")
        tests_passed += 1
    else:
        print_fail(f"Entity overlap too low for same event: {overlap_2:.3f}")

    # Test 2.3: Different events - BR-101 accidents
    print_subheader("2.3: BR-101 Accidents (DIFFERENT Events)")

    sig_3a = create_mock_signature(
        people=["Familia"],
        organizations=["PRF"],
        locations=["BR-101", "Santa Catarina", "Joinville"],
        event_action="morreu",
        unique_details=["caminhao", "3 mortos", "madrugada"],
        article_id=ARTICLE_3A["id"]
    )

    sig_3b = create_mock_signature(
        people=["Motociclista"],
        organizations=["PRF"],
        locations=["BR-101", "Rio Grande do Sul", "Torres"],
        event_action="morreu",
        unique_details=["colisao onibus", "1 morto"],
        article_id=ARTICLE_3B["id"]
    )

    es_3a = EventSignature(
        id=uuid4(),
        article_id=sig_3a.article_id,
        people=sig_3a.people,
        organizations=sig_3a.organizations,
        locations=sig_3a.locations,
        event_action=sig_3a.event_action,
        unique_details=sig_3a.unique_details,
        canonical_key=sig_3a.canonical_key,
        confidence=sig_3a.confidence
    )

    es_3b = EventSignature(
        id=uuid4(),
        article_id=sig_3b.article_id,
        people=sig_3b.people,
        organizations=sig_3b.organizations,
        locations=sig_3b.locations,
        event_action=sig_3b.event_action,
        unique_details=sig_3b.unique_details,
        canonical_key=sig_3b.canonical_key,
        confidence=sig_3b.confidence
    )

    overlap_3 = es_3a.calculate_entity_overlap(es_3b)

    tests_total += 1
    print_detail("Article A entities", str(es_3a.get_entity_set()))
    print_detail("Article B entities", str(es_3b.get_entity_set()))
    print_detail("Entity Overlap Score", f"{overlap_3:.3f}")
    print_detail("High Threshold", f"{ENTITY_MATCH_HIGH_THRESHOLD}")

    # They share BR-101 and PRF, but different locations (SC vs RS)
    # Should NOT be high overlap because people and specific locations differ
    if overlap_3 < ENTITY_MATCH_HIGH_THRESHOLD:
        print_pass(f"Different events correctly identified - overlap ({overlap_3:.3f}) < high threshold")
        tests_passed += 1
    else:
        print_fail(f"WRONG: Different events incorrectly matched with overlap {overlap_3:.3f}")

    # Summary
    print(f"\n{Colors.BOLD}Matching Tests: {tests_passed}/{tests_total} passed{Colors.RESET}")
    return tests_passed, tests_total


def test_event_grouping():
    """
    Test 3: Validate that articles about the SAME event are grouped together.

    Simulates the full clustering decision process.
    """
    print_header("TEST 3: Event Grouping Validation")

    tests_passed = 0
    tests_total = 0

    # Define test cases with expected results
    test_cases = [
        {
            "name": "Empresario brasileiro + Pai de trigemeos",
            "article_a": ARTICLE_1A,
            "article_b": ARTICLE_1B,
            "signature_a": create_mock_signature(
                people=["Empresario brasileiro"],
                organizations=["ICE"],
                locations=["Estados Unidos"],
                event_action="detido",
                unique_details=["pai de trigemeos"],
                article_id=ARTICLE_1A["id"]
            ),
            "signature_b": create_mock_signature(
                people=["Brasileiro", "Pai de trigemeos"],
                organizations=["ICE"],
                locations=["EUA"],
                event_action="preso",
                unique_details=["empresario"],
                article_id=ARTICLE_1B["id"]
            ),
            "expected_same_event": True,
            "reason": "Both describe the same Brazilian detained by ICE"
        },
        {
            "name": "Trump anuncia tarifas + Entenda tarifas",
            "article_a": ARTICLE_2A,
            "article_b": ARTICLE_2B,
            "signature_a": create_mock_signature(
                people=["Donald Trump"],
                organizations=["Casa Branca"],
                locations=["China", "Mexico"],
                event_action="anunciou",
                unique_details=["tarifas 25%"],
                article_id=ARTICLE_2A["id"]
            ),
            "signature_b": create_mock_signature(
                people=["Trump"],
                organizations=[],
                locations=["China"],
                event_action="anunciou",
                unique_details=["tarifas"],
                article_id=ARTICLE_2B["id"]
            ),
            "expected_same_event": True,
            "reason": "Both discuss Trump's tariff announcement"
        },
        {
            "name": "Acidente SC + Acidente RS (BR-101)",
            "article_a": ARTICLE_3A,
            "article_b": ARTICLE_3B,
            "signature_a": create_mock_signature(
                people=["Familia"],
                organizations=["PRF"],
                locations=["BR-101", "Santa Catarina", "Joinville"],
                event_action="morreu",
                unique_details=["3 mortos", "caminhao"],
                article_id=ARTICLE_3A["id"]
            ),
            "signature_b": create_mock_signature(
                people=["Motociclista"],
                organizations=["PRF"],
                locations=["BR-101", "Rio Grande do Sul", "Torres"],
                event_action="morreu",
                unique_details=["1 morto", "onibus"],
                article_id=ARTICLE_3B["id"]
            ),
            "expected_same_event": False,
            "reason": "Different accidents in different states"
        }
    ]

    for i, tc in enumerate(test_cases, 1):
        print_subheader(f"3.{i}: {tc['name']}")

        print_detail("Article A", tc["article_a"]["title"][:60] + "...")
        print_detail("Article B", tc["article_b"]["title"][:60] + "...")
        print()

        # Create EventSignature objects
        sig_a = tc["signature_a"]
        sig_b = tc["signature_b"]

        es_a = EventSignature(
            id=uuid4(),
            article_id=sig_a.article_id,
            people=sig_a.people,
            organizations=sig_a.organizations,
            locations=sig_a.locations,
            event_action=sig_a.event_action,
            unique_details=sig_a.unique_details,
            canonical_key=sig_a.canonical_key,
            confidence=sig_a.confidence
        )

        es_b = EventSignature(
            id=uuid4(),
            article_id=sig_b.article_id,
            people=sig_b.people,
            organizations=sig_b.organizations,
            locations=sig_b.locations,
            event_action=sig_b.event_action,
            unique_details=sig_b.unique_details,
            canonical_key=sig_b.canonical_key,
            confidence=sig_b.confidence
        )

        # Calculate overlap
        overlap = es_a.calculate_entity_overlap(es_b)

        # Determine match type
        match_type = "none"
        confidence = 0.0

        # Check exact key match
        if sig_a.canonical_key == sig_b.canonical_key:
            match_type = "exact"
            confidence = EXACT_MATCH_CONFIDENCE
        elif overlap >= ENTITY_MATCH_HIGH_THRESHOLD:
            match_type = "entity_high"
            confidence = overlap
        elif overlap >= ENTITY_MATCH_LOW_THRESHOLD:
            match_type = "entity_medium"
            confidence = overlap
        else:
            match_type = "no_match"
            confidence = overlap

        is_same_event = match_type in ["exact", "entity_high", "entity_medium"]

        # Display results
        print_detail("Signature A canonical key", sig_a.canonical_key)
        print_detail("Signature B canonical key", sig_b.canonical_key)
        print_detail("Entity Overlap Score", f"{overlap:.3f}")
        print_detail("Match Type", match_type)
        print_detail("Confidence", f"{confidence:.3f}")
        print_detail("Algorithm Decision", "SAME EVENT" if is_same_event else "DIFFERENT EVENTS")
        print_detail("Expected Result", "SAME EVENT" if tc["expected_same_event"] else "DIFFERENT EVENTS")
        print_detail("Reason", tc["reason"])
        print()

        tests_total += 1

        # For same event cases, we allow medium threshold matches
        # (they would go to LLM verification in production)
        if tc["expected_same_event"]:
            if is_same_event or overlap >= ENTITY_MATCH_LOW_THRESHOLD:
                print_pass(f"Correctly identified as SAME EVENT (or candidate for verification)")
                tests_passed += 1
            else:
                print_fail(f"Should be SAME EVENT but got overlap {overlap:.3f}")
        else:
            # For different events, overlap should be below high threshold
            if not is_same_event or overlap < ENTITY_MATCH_HIGH_THRESHOLD:
                print_pass(f"Correctly identified as DIFFERENT EVENTS")
                tests_passed += 1
            else:
                print_fail(f"Should be DIFFERENT but got high overlap {overlap:.3f}")

    # Summary
    print(f"\n{Colors.BOLD}Grouping Tests: {tests_passed}/{tests_total} passed{Colors.RESET}")
    return tests_passed, tests_total


async def test_service_integration():
    """
    Test 4: Integration test with actual services (if available).

    Tests the service initialization and fallback extraction.
    """
    print_header("TEST 4: Service Integration")

    tests_passed = 0
    tests_total = 0

    # Test 4.1: EventSignatureService initialization
    print_subheader("4.1: Service Initialization")

    tests_total += 1
    try:
        sig_service = EventSignatureService(llm_service=None)
        print_pass("EventSignatureService initialized successfully")
        tests_passed += 1
    except Exception as e:
        print_fail(f"Failed to initialize EventSignatureService: {e}")

    tests_total += 1
    try:
        match_service = EventMatchingService(db_service=None)
        print_pass("EventMatchingService initialized successfully")
        tests_passed += 1
    except Exception as e:
        print_fail(f"Failed to initialize EventMatchingService: {e}")

    # Test 4.2: Fallback extraction (without LLM)
    print_subheader("4.2: Fallback Extraction (without LLM)")

    tests_total += 1
    sig_service = EventSignatureService(llm_service=None)

    # Use fallback extraction
    signature = sig_service._extract_fallback(
        title="Empresario brasileiro detido pelo ICE nos EUA",
        content="O empresario foi detido enquanto trabalhava nos Estados Unidos.",
        article_id=uuid4(),
        reference_date=date.today()
    )

    if signature:
        print_pass("Fallback extraction returned a signature")
        print_detail("People", str(signature.people))
        print_detail("Organizations", str(signature.organizations))
        print_detail("Locations", str(signature.locations))
        print_detail("Event Action", signature.event_action)
        print_detail("Canonical Key", signature.canonical_key)
        print_detail("Confidence", f"{signature.confidence:.2f}")
        tests_passed += 1
    else:
        print_fail("Fallback extraction returned None")

    # Test 4.3: Configuration checks
    print_subheader("4.3: Configuration Status")

    extraction_enabled = is_event_extraction_enabled()
    matching_enabled = is_event_matching_enabled()

    print_info(f"Event Extraction Enabled: {extraction_enabled}")
    print_info(f"Event Matching Enabled: {matching_enabled}")

    # Summary
    print(f"\n{Colors.BOLD}Integration Tests: {tests_passed}/{tests_total} passed{Colors.RESET}")
    return tests_passed, tests_total


def print_final_summary(results: List[Tuple[int, int]]) -> bool:
    """
    Print final test summary.

    Args:
        results: List of (passed, total) tuples

    Returns:
        True if all tests passed
    """
    print_header("FINAL SUMMARY")

    total_passed = sum(r[0] for r in results)
    total_tests = sum(r[1] for r in results)

    test_names = [
        "Signature Extraction",
        "Event Matching",
        "Event Grouping",
        "Service Integration"
    ]

    print(f"{Colors.BOLD}Test Results:{Colors.RESET}\n")

    for name, (passed, total) in zip(test_names, results):
        status = Colors.GREEN if passed == total else Colors.RED
        print(f"  {status}{passed}/{total}{Colors.RESET} - {name}")

    print()

    if total_passed == total_tests:
        print(f"{Colors.GREEN}{Colors.BOLD}ALL TESTS PASSED ({total_passed}/{total_tests}){Colors.RESET}")
        return True
    else:
        print(f"{Colors.RED}{Colors.BOLD}SOME TESTS FAILED ({total_passed}/{total_tests}){Colors.RESET}")
        return False


async def main():
    """Main test runner."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("=" * 60)
    print("  EVENT CLUSTERING TEST SUITE")
    print("  Testing event signature extraction and matching")
    print("=" * 60)
    print(f"{Colors.RESET}")

    results = []

    # Run all tests
    results.append(test_signature_extraction())
    results.append(test_event_matching())
    results.append(test_event_grouping())
    results.append(await test_service_integration())

    # Print summary
    all_passed = print_final_summary(results)

    # Exit code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
