import requests
import json


class BioStudiesExtractor:
    """Class to handle BioStudies API interactions"""

    def __init__(self, collection: str = ""):
        self.base_url = "https://www.ebi.ac.uk/biostudies/api/v1"
        self.studies_url = self.base_url + "/studies"
        self.search_url = (
            f"{self.base_url}/{collection}/search"
            if collection
            else f"{self.base_url}/search"
        )

    def validate_study_id(self, study_id):
        """
        Validate BioStudies ID format

        Args:
            study_id (str): BioStudies accession ID

        Returns:
            tuple: (is_valid, cleaned_id, error_message)
        """
        if not study_id or not isinstance(study_id, str):
            return False, None, "Study ID is required"

        # Clean the study ID
        verified_id = study_id.strip().upper()

        # Basic format validation for common BioStudies ID patterns
        # Examples: S-ONTX26, E-MTAB-1234, S-BSST123
        import re

        patterns = [
            r"^S-[A-Z0-9]+$",  # Studies starting with S-
            r"^E-[A-Z]+-\d+$",  # Expression studies like E-MTAB-1234
            r"^[A-Z]+-\d+$",  # General pattern like BSST123
        ]

        if not any(re.match(pattern, verified_id) for pattern in patterns):
            return (
                False,
                verified_id,
                "Invalid BioStudies ID format. Expected format: S-ONTX26, E-MTAB-1234, etc.",
            )

        return True, verified_id, None

    def get_study_metadata(self, study_id):
        """
        Extract metadata for a given BioStudies ID

        Args:
            study_id (str): BioStudies accession ID (e.g., S-ONTX26)

        Returns:
            dict: Parsed metadata or error information
        """
        try:
            # Validate study ID format
            is_valid, verified_id, validation_error = self.validate_study_id(study_id)
            if not is_valid:
                return {"error": validation_error}

            # Construct API URL
            url = self.studies_url + f"/{verified_id}"

            # Make request with proper headers
            headers = {
                "Accept": "application/json",
                "User-Agent": "BioStudies-VHP4Safety-App/1.0",
            }

            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                try:
                    data = response.json()
                    if not data:
                        return {
                            "error": f"Empty response received for study {verified_id}"
                        }

                    # Parse metadata first, then build URL using the derived collection (no extra API calls)
                    md = self.parse_metadata(data)
                    collection = md.get("collection", "")
                    url = self.build_study_url(verified_id, collection).get("url", "")
                    return md | {"url": url}
                except json.JSONDecodeError as e:
                    return {
                        "error": f"Invalid JSON response from BioStudies API: {str(e)}"
                    }
            elif response.status_code == 404:
                return {
                    "error": f"Study '{verified_id}' not found in BioStudies database. Please check the ID and try again."
                }
            elif response.status_code == 403:
                return {
                    "error": "Access forbidden. The study may be restricted or private."
                }
            elif response.status_code == 500:
                return {"error": "BioStudies server error. Please try again later."}
            elif response.status_code == 503:
                return {
                    "error": "BioStudies service temporarily unavailable. Please try again later."
                }
            else:
                return {
                    "error": f"BioStudies API returned status {response.status_code}. Please try again later."
                }

        except requests.exceptions.Timeout:
            return {
                "error": "Request timed out. BioStudies server may be slow. Please try again."
            }
        except requests.exceptions.ConnectionError:
            return {
                "error": "Cannot connect to BioStudies server. Please check your internet connection."
            }
        except requests.exceptions.RequestException as e:
            return {"error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error occurred: {str(e)}"}

    def get_study_collection(self, study_id):
        """
        Extract collection for a given BioStudies ID

        Args:
            study_id (str): BioStudies accession ID (e.g., S-ONTX26)

        Returns:
            dict: Parsed collection or error information
        """
        metadata = self.get_study_metadata(study_id)
        if "error" in metadata:
            return metadata
        collection = metadata.get("collection", "")
        return {"accession": study_id, "collection": collection}

    def build_study_url(self, study_id, collection: str = ""):
        """
        Build the URL to access the study in BioStudies web interface

        Args:
            study_id (str): BioStudies accession
            collection (str): Optional collection name if already known
        Returns:
            dict: URL or error information
        """
        is_valid, verified_id, validation_error = self.validate_study_id(study_id)
        if not is_valid:
            return {"error": validation_error}

        # If collection is provided, use it; otherwise, build the non-collection URL
        if collection:
            url = f"https://www.ebi.ac.uk/biostudies/{collection}/studies/{verified_id}"
        else:
            url = f"https://www.ebi.ac.uk/biostudies/studies/{verified_id}"

        return {"accession": verified_id, "url": url}

    def search_studies(self, query, page=1, page_size=10) -> dict:
        """
        Search for studies in BioStudies database

        Args:
            query (str): Search query string
            page (int): Page number for pagination
            page_size (int): Number of results per page

        Returns:
            dict: Search results or error information
        """
        try:
            if not query or not isinstance(query, str):
                return {"error": "Search query must be a non-empty string."}

            params = {"query": query, "page": page, "pageSize": page_size}

            headers = {
                "Accept": "application/json",
                "User-Agent": "BioStudies-VHP4Safety-App/1.0",
            }

            response = requests.get(
                self.search_url, headers=headers, params=params, timeout=30
            )

            if response.status_code == 200:
                try:
                    data = response.json()
                    if not data or data.get("totalHits", 0) == 0:
                        return {"error": "No results found."}
                    return data | {"hits": self._hit_url(data.get("hits", []))}
                except json.JSONDecodeError as e:
                    return {
                        "error": f"Invalid JSON response from BioStudies API: {str(e)}"
                    }
            elif response.status_code == 400:
                return {"error": "Bad request. Please check your search parameters."}
            elif response.status_code == 403:
                return {"error": "Access forbidden. The collection may be restricted."}
            elif response.status_code == 500:
                return {"error": "BioStudies server error. Please try again later."}
            elif response.status_code == 503:
                return {
                    "error": "BioStudies service temporarily unavailable. Please try again later."
                }
            else:
                return {
                    "error": f"BioStudies API returned status {response.status_code}. Please try again later."
                }

        except requests.exceptions.Timeout:
            return {
                "error": "Request timed out. BioStudies server may be slow. Please try again."
            }
        except requests.exceptions.ConnectionError:
            return {
                "error": "Cannot connect to BioStudies server. Please check your internet connection."
            }
        except requests.exceptions.RequestException as e:
            return {"error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error occurred: {str(e)}"}

    def _hit_url(self, hits: list) -> list:
        for hit in hits:
            acc = hit.get("accession") or hit.get("accno")
            if acc:
                hit["url"] = self.build_study_url(acc).get("url", "")
        return hits

    def list_studies(
        self, page_size=50, max_pages=None, include_urls: bool = False
    ) -> dict:
        """
        List all public studies in the configured BioStudies collection by paginating through results.
        Uses page/pageSize (e.g., ?page=1&amp;pageSize=50) because some BioStudies endpoints ignore offset/size
        and always return the first page (default pageSize=20).
        """
        headers = {
            "Accept": "application/json",
            "User-Agent": "BioStudies-VHP4Safety-App/1.0",
        }

        results = []
        seen_accessions = set()
        page = 1
        pages_fetched = 0
        total_hits = None

        while True:
            params = {"page": page, "pageSize": page_size}
            try:
                response = requests.get(
                    self.search_url, headers=headers, params=params, timeout=30
                )
            except requests.exceptions.RequestException as e:
                return {
                    "error": f"Network error during listing: {e}",
                    "total": len(results),
                    "hits": results,
                }

            if response.status_code != 200:
                return {
                    "error": f"BioStudies API returned status {response.status_code} while listing.",
                    "total": len(results),
                    "hits": results,
                }

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                return {
                    "error": f"Invalid JSON response from BioStudies API: {str(e)}",
                    "total": len(results),
                    "hits": results,
                }

            if total_hits is None:
                total_hits = data.get("totalHits") or data.get("total") or 0

            hits = data.get("hits", [])
            if not hits:
                break

            # Add only new accessions in case the server keeps sending the same page
            new_items = []
            for h in hits:
                acc = h.get("accession") or h.get("accno")
                if acc and acc not in seen_accessions:
                    seen_accessions.add(acc)
                    if include_urls:
                        new_items.append(
                            h | {"url": self.build_study_url(acc).get("url", "")}
                        )
                    else:
                        new_items.append(h)

            if not new_items:
                # No new items -> stop to avoid infinite loop
                break

            results.extend(new_items)
            pages_fetched += 1

            # Stop when collected all known hits
            if total_hits and len(results) >= total_hits:
                break

            # Stop when we hit the last page (short page)
            if len(hits) < page_size:
                break

            # Safety cap
            if max_pages is not None and pages_fetched >= max_pages:
                break

            page += 1

        reported_total = total_hits if total_hits is not None else len(results)
        return {"total": reported_total, "hits": results}

    def parse_metadata(self, raw_data):
        """
        Parse and structure the metadata from BioStudies API response

        Args:
            raw_data (dict): Raw JSON response from API

        Returns:
            dict: Structured metadata
        """
        try:
            metadata = {
                "accession": raw_data.get("accno", "N/A"),
                "title": raw_data.get("title", "N/A"),
                "description": raw_data.get("description", "N/A"),
                "release_date": raw_data.get("rdate", "N/A"),
                "modification_date": raw_data.get("mdate", "N/A"),
                "type": raw_data.get("type", "N/A"),
                # VHP4Safety-specific attributes to be added: case study, regulatory question, flow 
            }
            metadata["collection"] = ""
            return metadata

        except Exception as e:
            return {
                "error": f"Failed to parse metadata: {str(e)}",
                "raw_data": raw_data,
            }
