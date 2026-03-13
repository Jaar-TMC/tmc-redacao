"""Audit repository - generation audit trail, LLM usage logs, and fact-check scans."""

import json
import logging
from typing import Optional

from .base import BaseRepository

logger = logging.getLogger(__name__)


class AuditRepository(BaseRepository):
    """Repository for audit trail and usage logging."""

    def insert_generation_audit(self, audit_data: dict) -> bool:
        """Insert a generation audit trail record.

        Non-blocking: errors are logged but never propagated.
        Long fields are truncated to prevent DB overflow.

        Args:
            audit_data: Dict with audit fields (see migration 004)

        Returns:
            True if inserted successfully, False otherwise
        """
        try:
            def _trunc(val, max_len):
                if val and isinstance(val, str) and len(val) > max_len:
                    return val[:max_len]
                return val

            def _json_trunc(val, max_len):
                if val is None:
                    return None
                s = json.dumps(val, ensure_ascii=False) if not isinstance(val, str) else val
                return _trunc(s, max_len)

            query = """
                INSERT INTO generation_audit_trail
                (article_id, theme_id, request_payload, system_prompt_hash,
                 user_prompt_text, enrichment_result, raw_llm_response,
                 verification_result, cove_applied, cove_reclassified,
                 safety_gate_decision, confidence_score, risk_level,
                 publish_blocked, block_reason, phase_timings, total_duration_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    audit_data.get('article_id'),
                    audit_data.get('theme_id'),
                    _json_trunc(audit_data.get('request_payload'), 5000),
                    _trunc(audit_data.get('system_prompt_hash'), 64),
                    _trunc(audit_data.get('user_prompt_text'), 5000),
                    _json_trunc(audit_data.get('enrichment_result'), 5000),
                    _trunc(audit_data.get('raw_llm_response'), 10000),
                    _json_trunc(audit_data.get('verification_result'), 10000),
                    1 if audit_data.get('cove_applied') else 0,
                    audit_data.get('cove_reclassified', 0),
                    _trunc(audit_data.get('safety_gate_decision'), 20),
                    audit_data.get('confidence_score'),
                    _trunc(audit_data.get('risk_level'), 20),
                    1 if audit_data.get('publish_blocked') else 0,
                    _trunc(audit_data.get('block_reason'), 500),
                    _json_trunc(audit_data.get('phase_timings'), 500),
                    audit_data.get('total_duration_ms'),
                ))
                conn.commit()

            logger.debug("Generation audit trail inserted successfully")
            return True

        except Exception as e:
            logger.warning(f"Failed to insert generation audit (non-blocking): {e}")
            return False

    def insert_llm_usage_log(self, log_data: dict) -> bool:
        """Insert an LLM usage log record for cost and performance tracking.

        Non-blocking: errors are logged but never propagated.

        Args:
            log_data: Dict with fields matching llm_usage_log table

        Returns:
            True if inserted successfully, False otherwise
        """
        try:
            def _trunc(val, max_len):
                if val and isinstance(val, str) and len(val) > max_len:
                    return val[:max_len]
                return val

            query = """
                INSERT INTO llm_usage_log
                (correlation_id, task_type, model, endpoint, provider,
                 input_tokens, output_tokens, input_cost_usd, output_cost_usd,
                 latency_ms, status, error_message, response_chars, stop_reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    _trunc(log_data.get('correlation_id'), 64),
                    _trunc(log_data.get('task_type', 'unknown'), 50),
                    _trunc(log_data.get('model'), 100),
                    _trunc(log_data.get('endpoint'), 500),
                    _trunc(log_data.get('provider', 'anthropic'), 20),
                    log_data.get('input_tokens'),
                    log_data.get('output_tokens'),
                    log_data.get('input_cost_usd'),
                    log_data.get('output_cost_usd'),
                    log_data.get('latency_ms'),
                    _trunc(log_data.get('status', 'success'), 10),
                    _trunc(log_data.get('error_message'), 500),
                    log_data.get('response_chars'),
                    _trunc(log_data.get('stop_reason'), 20),
                ))
                conn.commit()

            return True

        except Exception as e:
            logger.warning(f"Failed to insert LLM usage log (non-blocking): {e}")
            return False

    def insert_fact_check_scan(self, scan_data: dict) -> bool:
        """Insert a fact-check scan record.

        Non-blocking: errors are logged but never propagated.

        Args:
            scan_data: Dict with scan fields (see migration 014)

        Returns:
            True if inserted successfully, False otherwise
        """
        try:
            def _trunc(val, max_len):
                if val and isinstance(val, str) and len(val) > max_len:
                    return val[:max_len]
                return val

            def _json_trunc(val, max_len):
                if val is None:
                    return None
                s = json.dumps(val, ensure_ascii=False) if not isinstance(val, str) else val
                return _trunc(s, max_len)

            query = """
                INSERT INTO fact_check_scans
                (scan_id, user_id, user_article_id, article_text_hash,
                 article_char_count, safety_index, safety_label,
                 total_claims, grounded_claims, fabricated_claims,
                 unverifiable_claims, corroboration_score,
                 external_factcheck_matches, scan_result, scan_duration_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    _trunc(scan_data.get('scan_id'), 64),
                    scan_data.get('user_id'),
                    scan_data.get('user_article_id'),
                    _trunc(scan_data.get('article_text_hash'), 64),
                    scan_data.get('article_char_count'),
                    scan_data.get('safety_index'),
                    _trunc(scan_data.get('safety_label'), 20),
                    scan_data.get('total_claims', 0),
                    scan_data.get('grounded_claims', 0),
                    scan_data.get('fabricated_claims', 0),
                    scan_data.get('unverifiable_claims', 0),
                    scan_data.get('corroboration_score'),
                    scan_data.get('external_factcheck_matches', 0),
                    _json_trunc(scan_data.get('scan_result'), 10000),
                    scan_data.get('scan_duration_ms'),
                ))
                conn.commit()

            logger.debug("Fact-check scan record inserted successfully")
            return True

        except Exception as e:
            logger.warning(f"Failed to insert fact-check scan (non-blocking): {e}")
            return False

    def get_latest_scan(self, article_text_hash: str, max_age_seconds: int = 300) -> Optional[dict]:
        """Look up the most recent scan for a given article text hash.

        Used for caching: if an identical article was scanned recently,
        return the cached result instead of re-scanning.

        Args:
            article_text_hash: SHA-256 hash of the article text
            max_age_seconds: Maximum age of cached result (default 5 minutes)

        Returns:
            dict with scan fields or None if no recent scan found
        """
        try:
            query = """
                SELECT TOP 1
                    scan_id, safety_index, safety_label,
                    total_claims, grounded_claims, fabricated_claims,
                    unverifiable_claims, corroboration_score,
                    external_factcheck_matches, scan_result,
                    scan_duration_ms, created_at
                FROM fact_check_scans
                WHERE article_text_hash = %s
                  AND created_at >= DATEADD(second, -%s, GETUTCDATE())
                ORDER BY created_at DESC
            """

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (article_text_hash, max_age_seconds))
                row = cursor.fetchone()

            if not row:
                return None

            result = {
                "scan_id": row[0],
                "safety_index": row[1],
                "safety_label": row[2],
                "total_claims": row[3],
                "grounded_claims": row[4],
                "fabricated_claims": row[5],
                "unverifiable_claims": row[6],
                "corroboration_score": row[7],
                "external_factcheck_matches": row[8],
                "scan_result": row[9],
                "scan_duration_ms": row[10],
                "created_at": row[11].isoformat() if row[11] else None,
            }

            # Parse scan_result JSON if present
            if result["scan_result"]:
                try:
                    result["scan_result"] = json.loads(result["scan_result"])
                except (json.JSONDecodeError, TypeError):
                    pass

            logger.debug(f"Cache hit for scan hash {article_text_hash[:16]}...")
            return result

        except Exception as e:
            logger.warning(f"Failed to get latest scan (non-blocking): {e}")
            return None
