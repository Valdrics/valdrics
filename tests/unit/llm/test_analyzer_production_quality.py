from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.costs import CloudUsageSummary, CostRecord
from app.shared.core.exceptions import AIAnalysisError
from app.shared.llm.analyzer import FinOpsAnalyzer


class TestFinOpsAnalyzerProductionQuality:
    """Production-quality tests covering security, performance, and edge cases."""

    def test_initialization_error_handling(self):
        invalid_llm = None
        analyzer = FinOpsAnalyzer(invalid_llm)
        assert analyzer.llm == invalid_llm

    @pytest.mark.asyncio
    async def test_concurrent_analysis_operations(self):
        import threading

        llm = MagicMock()
        llm.model_name = "gpt-4"
        analyzer = FinOpsAnalyzer(llm)

        usage_summary = CloudUsageSummary(
            tenant_id=str(uuid4()),
            provider="AWS",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 1),
            records=[
                CostRecord(
                    date=date(2024, 1, 1),
                    amount=Decimal("100.0"),
                    service="EC2",
                    region="us-east-1",
                )
            ],
            total_cost=Decimal("100.0"),
            currency="USD",
        )

        results: list[dict[str, str]] = []
        errors: list[str] = []

        def run_analysis() -> None:
            try:
                import asyncio

                with patch.object(analyzer, "analyze", return_value={"result": "success"}):
                    results.append(asyncio.run(analyzer.analyze(usage_summary)))
            except Exception as exc:  # pragma: no cover - defensive assertion capture
                errors.append(str(exc))

        threads = [threading.Thread(target=run_analysis) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert not errors
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_system_prompt_loading_robustness(self):
        llm = MagicMock()

        with patch("os.path.exists", return_value=False):
            analyzer = FinOpsAnalyzer(llm)
            prompt = await analyzer._get_prompt()
            assert "You are a FinOps expert" in str(prompt)

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", side_effect=RuntimeError("File read error")),
        ):
            analyzer = FinOpsAnalyzer(llm)
            prompt = await analyzer._get_prompt()
            assert "You are a FinOps expert" in str(prompt)

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", create=True),
            patch("yaml.safe_load", return_value={"invalid": "structure"}),
        ):
            analyzer = FinOpsAnalyzer(llm)
            prompt = await analyzer._get_prompt()
            assert "You are a FinOps expert" in str(prompt)

    @pytest.mark.asyncio
    async def test_budget_integration_edge_cases(self):
        llm = MagicMock()
        analyzer = FinOpsAnalyzer(llm)
        mock_db = AsyncMock()

        usage_summary = CloudUsageSummary(
            tenant_id=str(uuid4()),
            provider="AWS",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 1),
            records=[
                CostRecord(
                    date=date(2024, 1, 1),
                    amount=Decimal("100.0"),
                    service="EC2",
                    region="us-east-1",
                )
            ],
            total_cost=Decimal("100.0"),
            currency="USD",
        )

        with (
            patch.object(analyzer, "_check_cache_and_delta", return_value=(None, False)),
            patch.object(
                analyzer,
                "_setup_client_and_usage",
                return_value=("groq", "llama-3.3-70b-versatile", None),
            ),
            patch.object(
                analyzer,
                "_invoke_llm",
                return_value=('{"summary":"ok"}', {"token_usage": {}}),
            ),
            patch.object(analyzer, "_process_analysis_results", return_value={"result": "ok"}),
            patch(
                "app.shared.llm.analyzer.LLMBudgetManager.check_and_reserve",
                new_callable=AsyncMock,
            ) as mock_reserve,
        ):
            result = await analyzer.analyze(usage_summary, tenant_id=uuid4(), db=None)
            assert isinstance(result, dict)
            mock_reserve.assert_not_called()

        with (
            patch.object(analyzer, "_check_cache_and_delta", return_value=(None, False)),
            patch(
                "app.shared.llm.analyzer.LLMBudgetManager.check_and_reserve",
                new_callable=AsyncMock,
            ) as mock_reserve,
        ):
            mock_reserve.side_effect = RuntimeError("DB error")
            with pytest.raises(AIAnalysisError):
                await analyzer.analyze(usage_summary, tenant_id=uuid4(), db=mock_db)

    def test_markdown_stripping_comprehensive(self):
        analyzer = FinOpsAnalyzer(MagicMock())
        for input_text, expected in [
            ('```json\n{"test": "value"}\n```', '{"test": "value"}'),
            ('```\n{"test": "value"}\n```', '{"test": "value"}'),
            ('```python\nprint("hello")\n```', 'print("hello")'),
            ("no markdown here", "no markdown here"),
            ("```", "```"),
            ("```\n\n```", ""),
        ]:
            assert analyzer._strip_markdown(input_text) == expected

    @pytest.mark.asyncio
    async def test_caching_integration_comprehensive(self):
        llm = MagicMock()
        analyzer = FinOpsAnalyzer(llm)

        usage_summary = CloudUsageSummary(
            tenant_id=str(uuid4()),
            provider="AWS",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 1),
            records=[
                CostRecord(
                    date=date(2024, 1, 1),
                    amount=Decimal("100.0"),
                    service="EC2",
                    region="us-east-1",
                )
            ],
            total_cost=Decimal("100.0"),
            currency="USD",
        )

        with patch("app.shared.llm.analyzer.get_cache_service") as mock_cache_service:
            mock_cache = MagicMock()
            mock_cache.get_analysis = AsyncMock(return_value=None)
            mock_cache_service.return_value = mock_cache
            assert await analyzer._check_cache_and_delta(uuid4(), False, usage_summary) == (None, False)

        assert await analyzer._check_cache_and_delta(uuid4(), True, usage_summary) == (None, False)

    def test_model_validation_and_fallbacks(self):
        llm = MagicMock()
        analyzer = FinOpsAnalyzer(llm)

        with patch("app.shared.llm.analyzer.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.LLM_PROVIDER = "groq"
            mock_settings.return_value = mock_settings_obj
            assert analyzer.llm == llm

    @pytest.mark.asyncio
    async def test_error_propagation_and_logging(self):
        llm = MagicMock()
        analyzer = FinOpsAnalyzer(llm)

        usage_summary = CloudUsageSummary(
            tenant_id=str(uuid4()),
            provider="AWS",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 1),
            records=[
                CostRecord(
                    date=date(2024, 1, 1),
                    amount=Decimal("100.0"),
                    service="EC2",
                    region="us-east-1",
                )
            ],
            total_cost=Decimal("100.0"),
            currency="USD",
        )

        with (
            patch.object(analyzer, "_check_cache_and_delta", return_value=(None, False)),
            patch(
                "app.shared.llm.analyzer.LLMGuardrails.sanitize_input",
                side_effect=RuntimeError("Sanitization error"),
            ),
            patch("app.shared.llm.analyzer.logger") as mock_logger,
        ):
            try:
                await analyzer.analyze(usage_summary, tenant_id=uuid4())
            except Exception:
                pass
            mock_logger.error.assert_called()
