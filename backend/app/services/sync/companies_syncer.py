import logging
from typing import Set

from app.services.sync.base import BaseSyncer
from app.models import Company
from app.integrations.productboard import ProductBoardClient, CompaniesAPI

logger = logging.getLogger(__name__)


class CompaniesSyncer(BaseSyncer[Company]):
    """Syncs companies from ProductBoard."""

    entity_type = "companies"

    async def sync(self) -> int:
        """Sync companies from ProductBoard (incremental)."""
        self.start_sync()
        last_sync = self.get_last_sync_time()

        try:
            async with ProductBoardClient() as client:
                api = CompaniesAPI(client)
                pb_companies = await api.list_companies(updated_after=last_sync)

                count = 0
                for pb_company in pb_companies:
                    self._upsert_company(pb_company)
                    count += 1

                self.db.commit()
                self.complete_sync(count)
                return count

        except Exception as e:
            self.fail_sync(str(e))
            raise

    async def sync_missing_from_ids(self, company_ids: Set[str]) -> int:
        """Fetch companies by ID that we don't have in our database."""
        existing = {c.pb_id for c in self.db.query(Company.pb_id).all()}
        missing = company_ids - existing

        if not missing:
            return 0

        logger.info(f"Fetching {len(missing)} missing companies by ID...")

        count = 0
        async with ProductBoardClient() as client:
            api = CompaniesAPI(client)
            for pb_id in missing:
                try:
                    pb_company = await api.get_company(pb_id)
                    if pb_company:
                        self._upsert_company(pb_company)
                        count += 1
                except Exception as e:
                    logger.warning(f"Failed to fetch company {pb_id}: {e}")

        self.db.commit()
        return count

    def _upsert_company(self, pb_company: dict):
        """Insert or update a company."""
        pb_id = pb_company.get("id")

        company = self.db.query(Company).filter(Company.pb_id == pb_id).first()

        if not company:
            company = Company(pb_id=pb_id)
            self.db.add(company)

        company.name = pb_company.get("name")
        company.domain = pb_company.get("domain")

        # Custom fields if available
        custom_fields = pb_company.get("customFields", {})
        if custom_fields:
            company.customer_id = custom_fields.get("customer_id")
            company.account_sales_theatre = custom_fields.get("account_sales_theatre")
            company.cse = custom_fields.get("cse")
            company.account_type = custom_fields.get("account_type")
