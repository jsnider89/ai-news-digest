"""High-level orchestration helpers for newsletters."""
from __future__ import annotations

import logging

from app.data.database import session_scope
from app.data import repositories
from app.tasks.pipeline import NewsletterPipeline
from app.utils.run_logs import capture_run_logs

logger = logging.getLogger("market_aggregator.service")


async def run_newsletter_once(newsletter_id: int) -> dict:
    """Run the pipeline for a single newsletter and persist the results."""
    async with session_scope() as session:
        newsletter = await repositories.get_newsletter(session, newsletter_id)
        if not newsletter:
            raise ValueError(f"Newsletter {newsletter_id} not found")
        config = repositories.to_pipeline_config(newsletter)
        pipeline = NewsletterPipeline()

        run_record = await repositories.create_run_record(session, newsletter_id=newsletter.id)
        response: dict | None = None
        with capture_run_logs() as captured_logs:
            result = await pipeline.run(config)

            subject = result.subject or f"{newsletter.name} Digest"
            html_content = result.html_content or ""
            stored_run = await repositories.store_run_result(
                session,
                newsletter_id=newsletter.id,
                run=run_record,
                pipeline_result=result,
                html_content=html_content,
                subject=subject,
            )

            # Note: session.commit() will be called by session_scope() context manager

            logger.info("Run complete for newsletter %s", newsletter.name)
            response = {
                "newsletter_id": newsletter.id,
                "success": result.success,
                "ai_provider": result.ai_provider,
                "articles": result.article_count,
                "feed_statuses": list(result.feed_statuses),
                "subject": subject,
                "run_id": stored_run.id,
            }

        if response is None:  # pragma: no cover - defensive
            raise RuntimeError("Run response not generated")

        # Try to append logs, but don't fail the entire run if this fails
        try:
            await repositories.append_run_logs(
                session,
                run_id=response["run_id"],
                entries=[
                    {
                        "timestamp": entry["timestamp"],
                        "level": entry["level"],
                        "logger": entry["logger"],
                        "message": entry["message"],
                        "exception": entry.get("exception"),
                    }
                    for entry in captured_logs
                ],
            )
            logger.info("Successfully appended %d log entries for run %s", len(captured_logs), response["run_id"])
        except Exception as exc:
            logger.error("Failed to append run logs for run %s: %s", response["run_id"], exc, exc_info=True)

        return response
