import os
from typing import Dict, Any, List
from app.utils.logger import get_logger
from app.database.supabase_client import get_supabase_client

logger = get_logger(__name__)


class SearchHandler:
    """
    Handles diamond search queries with natural language processing.
    Converts user queries into structured database searches and ranks results.
    """

    def __init__(self):
        self.supabase = get_supabase_client()

    async def search(self, query: str,
                     intent_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute diamond search based on natural language query.

        Args:
            query: User's search query
            intent_result: Parsed intent with extracted entities

        Returns:
            Dict with success status and listings
        """
        try:
            logger.info(f"Executing search for: {query}")

            # Extract search parameters from entities
            entities = intent_result.get("entities", {})
            search_params = self._build_search_params(entities)

            # Execute database query
            listings = await self._query_database(search_params)

            # Rank and sort results
            ranked_listings = self._rank_results(listings, search_params)

            return {
                "success": True,
                "listings": ranked_listings,
                "count": len(ranked_listings),
                "search_params": search_params
            }

        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "listings": [],
                "count": 0
            }

    def _build_search_params(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build structured search parameters from extracted entities.

        Args:
            entities: Extracted entities from intent detection

        Returns:
            Structured search parameters
        """
        params = {"filters": {}, "ranges": {}}

        # Exact match filters
        if entities.get("shape"):
            params["filters"]["shape"] = entities["shape"]

        if entities.get("color"):
            params["filters"]["color"] = entities["color"]

        if entities.get("clarity"):
            params["filters"]["clarity"] = entities["clarity"]

        if entities.get("cut"):
            params["filters"]["cut"] = entities["cut"]

        # Range filters
        if entities.get("carat_min") or entities.get("carat_max"):
            params["ranges"]["carat"] = {
                "min": entities.get("carat_min"),
                "max": entities.get("carat_max")
            }

        if entities.get("price_min") or entities.get("price_max"):
            params["ranges"]["price"] = {
                "min": entities.get("price_min"),
                "max": entities.get("price_max")
            }

        return params

    async def _query_database(
            self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Query Supabase database with search parameters.

        Args:
            search_params: Structured search parameters

        Returns:
            List of matching listings
        """
        try:
            # Start with base query - only approved listings
            query = self.supabase.table("listings").select("*").eq(
                "status", "approved")

            # Apply exact match filters
            filters = search_params.get("filters", {})
            for field, value in filters.items():
                # Search in gia_data JSON field
                query = query.contains("gia_data", {field: value})

            # Execute query
            response = query.execute()
            listings = response.data

            # Apply range filters in Python (as JSON queries are limited)
            ranges = search_params.get("ranges", {})
            if ranges:
                listings = self._apply_range_filters(listings, ranges)

            logger.info(f"Found {len(listings)} listings matching search")
            return listings

        except Exception as e:
            logger.error(f"Database query error: {str(e)}")
            return []

    def _apply_range_filters(self, listings: List[Dict],
                             ranges: Dict[str, Any]) -> List[Dict]:
        """
        Apply range filters to listings.

        Args:
            listings: List of listings from database
            ranges: Range filters to apply

        Returns:
            Filtered listings
        """
        filtered = []

        for listing in listings:
            gia_data = listing.get("gia_data", {})

            # Check carat range
            if "carat" in ranges:
                carat = float(gia_data.get("carat", 0))
                carat_range = ranges["carat"]

                if carat_range.get("min") and carat < carat_range["min"]:
                    continue
                if carat_range.get("max") and carat > carat_range["max"]:
                    continue

            # Check price range
            if "price" in ranges:
                price_str = listing.get("price", "0")

                # Skip "Contact for Price" listings in price searches
                if price_str == "Contact for Price":
                    continue

                try:
                    # Remove currency symbols and commas
                    price = float(price_str.replace("$", "").replace(",", ""))
                    price_range = ranges["price"]

                    if price_range.get("min") and price < price_range["min"]:
                        continue
                    if price_range.get("max") and price > price_range["max"]:
                        continue
                except ValueError:
                    continue

            filtered.append(listing)

        return filtered

    def _rank_results(self, listings: List[Dict],
                      search_params: Dict[str, Any]) -> List[Dict]:
        """
        Rank search results by relevance.

        Priority:
        1. Exact matches for all criteria
        2. Exact matches for most criteria
        3. Partial matches
        4. Sort by freshness (newest first)

        Args:
            listings: List of listings to rank
            search_params: Search parameters used

        Returns:
            Ranked and sorted listings
        """
        if not listings:
            return []

        filters = search_params.get("filters", {})

        # Calculate match score for each listing
        for listing in listings:
            gia_data = listing.get("gia_data", {})
            score = 0

            # Exact match scoring
            for field, value in filters.items():
                if gia_data.get(field) == value:
                    score += 10
                elif str(gia_data.get(field,
                                      "")).lower() == str(value).lower():
                    score += 5

            # Range match scoring
            ranges = search_params.get("ranges", {})
            if "carat" in ranges:
                carat = float(gia_data.get("carat", 0))
                carat_range = ranges["carat"]

                # Higher score for being in middle of range
                if carat_range.get("min") and carat_range.get("max"):
                    mid = (carat_range["min"] + carat_range["max"]) / 2
                    distance = abs(carat - mid)
                    score += max(0, 5 - distance)

            listing["_search_score"] = score

        # Sort by score (descending), then by created_at (newest first)
        listings.sort(key=lambda x:
                      (x.get("_search_score", 0), x.get("created_at", "")),
                      reverse=True)

        # Remove score field before returning
        for listing in listings:
            listing.pop("_search_score", None)

        return listings

    def build_search_url(self, query: str, intent_result: Dict[str,
                                                               Any]) -> str:
        """
        Build a shareable search URL with query parameters.

        Args:
            query: Original search query
            intent_result: Parsed intent with entities

        Returns:
            URL-encoded search string
        """
        from urllib.parse import urlencode

        params = {}
        entities = intent_result.get("entities", {})

        if entities.get("shape"):
            params["shape"] = entities["shape"]
        if entities.get("color"):
            params["color"] = entities["color"]
        if entities.get("clarity"):
            params["clarity"] = entities["clarity"]
        if entities.get("cut"):
            params["cut"] = entities["cut"]
        if entities.get("carat_min"):
            params["carat_min"] = entities["carat_min"]
        if entities.get("carat_max"):
            params["carat_max"] = entities["carat_max"]
        if entities.get("price_min"):
            params["price_min"] = entities["price_min"]
        if entities.get("price_max"):
            params["price_max"] = entities["price_max"]

        if params:
            return f"/search?{urlencode(params)}"
        else:
            return f"/search?q={query}"

    async def get_listing_details(self, listing_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific listing.

        Args:
            listing_id: Listing ID

        Returns:
            Complete listing details
        """
        try:
            response = self.supabase.table("listings").select("*").eq(
                "id", listing_id).single().execute()

            if response.data:
                return {"success": True, "listing": response.data}
            else:
                return {"success": False, "error": "Listing not found"}

        except Exception as e:
            logger.error(f"Error fetching listing details: {str(e)}")
            return {"success": False, "error": str(e)}
