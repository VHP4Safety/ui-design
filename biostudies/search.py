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

    def search_studies(self, query, page=1, page_size=10, load_metadate:bool=True, filter:tuple=tuple()) -> dict:
        """
        Search for studies in BioStudies database

        Args:
            query (str): Search query string
            page (int): Page number for pagination
            page_size (int): Number of results per page
            load_metadate (bool): Whether to load metadata for each hit (default: True)
                Only use when page_size is small to avoid performance issues
            filter (tuple): Optional tuple of (field, value) to filter results (default: no filter)

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
    
    def _hit_metadata(self, hits: list) -> list:
        for hit in hits:
            acc = hit.get("accession") or hit.get("accno")
            if acc:
                hit["metadata"] = self.get_study_metadata(acc)
        return hits

    def list_studies(
        self, page=1, page_size=50, include_urls: bool = False
    ) -> dict:
        """
        List studies in the configured BioStudies collection for a specific page.
        
        Args:
            page (int): Page number for pagination (default: 1)
            page_size (int): Number of results per page (default: 50)
            include_urls (bool): Whether to include study URLs in results (default: False)
            
        Returns:
            dict: Dictionary containing 'total' (total number of studies) and 'hits' (list of studies for the requested page)
        """
        headers = {
            "Accept": "application/json",
            "User-Agent": "BioStudies-VHP4Safety-App/1.0",
        }

        params = {"page": page, "pageSize": page_size}
        
        try:
            response = requests.get(
                self.search_url, headers=headers, params=params, timeout=30
            )
        except requests.exceptions.RequestException as e:
            return {
                "error": f"Network error during listing: {e}",
                "total": 0,
                "hits": [],
            }

        if response.status_code != 200:
            return {
                "error": f"BioStudies API returned status {response.status_code} while listing.",
                "total": 0,
                "hits": [],
            }

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            return {
                "error": f"Invalid JSON response from BioStudies API: {str(e)}",
                "total": 0,
                "hits": [],
            }

        total_hits = data.get("totalHits") or data.get("total") or 0
        hits = data.get("hits", [])
        
        # Add URLs if requested
        if include_urls:
            hits = self._hit_url(hits)
        
        return {"total": total_hits, "hits": hits}

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
                "attributes": [],
                "authors": [],
                "files": [],
                "links": [],
                "protocols": [],
                "publications": [],
                "organizations": [],
                "biological_context": {},
                "technical_details": {},
                "experimental_design": {},
                "raw_data": raw_data  # Keep raw data for debugging
            }
            
            # Extract attributes with enhanced categorization
            if "attributes" in raw_data:
                for attr in raw_data["attributes"]:
                    attr_name = attr.get("name", "").lower()
                    attr_value = attr.get("value", "")
                    
                    metadata["attributes"].append({
                        "name": attr.get("name", ""),
                        "value": attr_value
                    })
                    # add collection
                    if attr_name == "attachto":
                        metadata["collection"] = attr_value

                    # VHP4Safety filterable fields
                    
                    elif attr_name == "case study":
                        metadata["case_study"] = attr_value

                    elif attr_name == "regulatory question":
                        metadata["regulatory_question"] = attr_value
                    
                    elif attr_name == "flow step":
                        metadata["flow_step"] = attr_value
                    
                    # Categorize biological context
                    elif attr_name in ["organism", "species", "organism part", "organ", "cell type", "tissue", "disease", "disease state", "sample type"]:
                        metadata["biological_context"][attr_name] = attr_value
                    
                    # Categorize technical details
                    elif attr_name in ["platform", "instrument", "assay", "assay type", "library strategy", "library source", "data type", "sequencing mode", "sequencing date", "index adapters", "pipeline"]:
                        metadata["technical_details"][attr_name] = attr_value
                    
                    # Extract authors
                    elif attr_name in ["author", "authors", "contact", "submitter"]:
                        if attr_value not in metadata["authors"]:
                            metadata["authors"].append(attr_value)
            
            # Build organization lookup table first
            organization_lookup = {}
            if "section" in raw_data:
                self._build_organization_lookup(raw_data["section"], organization_lookup)
            
            # Process main section attributes first (this contains the main study metadata)
            if "section" in raw_data and "attributes" in raw_data["section"]:
                for attr in raw_data["section"]["attributes"]:
                    attr_name = attr.get("name", "").lower()
                    attr_value = attr.get("value", "")
                    
                    # Update title and description from section if not found at top level
                    if attr_name == "title" and metadata["title"] == "N/A":
                        metadata["title"] = attr_value
                    elif attr_name == "description" and metadata["description"] == "N/A":
                        metadata["description"] = attr_value
                    
                    # Categorize biological context
                    elif attr_name in ["organism", "species", "organism part", "organ", "cell type", "tissue", "disease", "disease state", "sample type"]:
                        metadata["biological_context"][attr_name] = attr_value
                    
                    # Categorize technical details
                    elif attr_name in ["platform", "instrument", "assay", "assay type", "library strategy", "library source", "data type", "sequencing mode", "sequencing date", "index adapters", "pipeline"]:
                        metadata["technical_details"][attr_name] = attr_value
                    
                    # Add to main attributes as well
                    metadata["attributes"].append({
                        "name": attr.get("name", ""),
                        "value": attr_value
                    })
            
            # Process sections for enhanced metadata extraction
            if "section" in raw_data:
                self._extract_comprehensive_metadata(raw_data["section"], metadata, organization_lookup)
            
            # Extract links with better categorization
            if "links" in raw_data:
                for link in raw_data["links"]:
                    link_data = {
                        "url": link.get("url", ""),
                        "type": link.get("type", ""),
                        "description": link.get("description", "")
                    }
                    metadata["links"].append(link_data)
                    
                    # Check if it's a publication link
                    link_type = link.get("type", "").lower()
                    if "doi" in link_type or "pubmed" in link_type or "publication" in link_type:
                        metadata["publications"].append(link_data)
            
            return metadata
            
        except Exception as e:
            return {"error": f"Failed to parse metadata: {str(e)}", "raw_data": raw_data}
    
    def _build_organization_lookup(self, section, org_lookup):
        """Build a lookup table for organization references"""
        if isinstance(section, dict):
            # Look for organization sections
            if section.get("type", "").lower() in ["organization", "organisation"]:
                org_id = section.get("accno", "")
                if org_id and "attributes" in section:
                    org_data = {}
                    for attr in section["attributes"]:
                        attr_name = attr.get("name", "").lower()
                        attr_value = attr.get("value", "")
                        if attr_name in ["name", "organization", "email", "address", "department", "affiliation"]:
                            org_data[attr_name] = attr_value
                    if org_data:
                        org_lookup[org_id] = org_data
            
            # Process subsections recursively
            if "subsections" in section:
                for subsection in section["subsections"]:
                    self._build_organization_lookup(subsection, org_lookup)
        
        elif isinstance(section, list):
            for item in section:
                self._build_organization_lookup(item, org_lookup)

    def _extract_comprehensive_metadata(self, section, metadata, organization_lookup=None):
        """Comprehensively extract all metadata from sections and subsections"""
        if organization_lookup is None:
            organization_lookup = {}
        if isinstance(section, dict):
            # Extract files
            if "files" in section:
                for file_info in section["files"]:
                    metadata["files"].append({
                        "name": file_info.get("name", ""),
                        "size": file_info.get("size", ""),
                        "type": file_info.get("type", ""),
                        "path": file_info.get("path", ""),
                        "description": file_info.get("description", "")
                    })
            
            # Extract protocols
            if section.get("type", "").lower() == "protocols" or "protocol" in section.get("type", "").lower():
                if "subsections" in section:
                    for protocol in section["subsections"]:
                        protocol_data = {
                            "type": protocol.get("type", ""),
                            "description": protocol.get("description", ""),
                            "attributes": []
                        }
                        
                        if "attributes" in protocol:
                            for attr in protocol["attributes"]:
                                protocol_data["attributes"].append({
                                    "name": attr.get("name", ""),
                                    "value": attr.get("value", "")
                                })
                        
                        metadata["protocols"].append(protocol_data)
            
            # Extract author and organization information
            if section.get("type", "").lower() in ["author", "contact", "person"]:
                if "attributes" in section:
                    author_info = {}
                    author_affiliation_ref = None
                    
                    for attr in section["attributes"]:
                        attr_name = attr.get("name", "").lower()
                        attr_value = attr.get("value", "")
                        
                        if attr_name in ["name", "first name", "last name", "email", "e-mail"]:
                            author_info[attr_name] = attr_value
                        elif attr_name == "affiliation" and attr.get("reference"):
                            author_affiliation_ref = attr_value
                    
                    if author_info:
                        author_name = author_info.get("name", "")
                        if not author_name:
                            # Construct name from first/last
                            first = author_info.get("first name", "")
                            last = author_info.get("last name", "")
                            author_name = f"{first} {last}".strip()
                        
                        # Create author entry with affiliation info
                        email = author_info.get("email") or author_info.get("e-mail", "")
                        author_entry = {
                            "name": author_name,
                            "email": email,
                            "affiliation_ref": author_affiliation_ref,
                            "affiliation_name": ""
                        }
                        
                        # Resolve affiliation if reference exists
                        if author_affiliation_ref and author_affiliation_ref in organization_lookup:
                            resolved_org = organization_lookup[author_affiliation_ref]
                            author_entry["affiliation_name"] = resolved_org.get("name", "")
                        
                        if author_name:
                            # Check if author already exists to avoid duplicates
                            existing_author = next((a for a in metadata.get("author_details", []) if a["name"] == author_name), None)
                            if not existing_author:
                                if "author_details" not in metadata:
                                    metadata["author_details"] = []
                                metadata["author_details"].append(author_entry)
                            
                            # Keep simple authors list for backward compatibility
                            if author_name not in metadata["authors"]:
                                metadata["authors"].append(author_name)
            
            # Extract experimental design information
            if "attributes" in section:
                for attr in section["attributes"]:
                    attr_name = attr.get("name", "").lower()
                    attr_value = attr.get("value", "")
                    
                    if attr_name in ["experimental factor", "variable", "treatment", "condition", "time point"]:
                        if "factors" not in metadata["experimental_design"]:
                            metadata["experimental_design"]["factors"] = []
                        metadata["experimental_design"]["factors"].append({
                            "name": attr_name,
                            "value": attr_value
                        })
            
            # Process subsections recursively
            if "subsections" in section:
                for subsection in section["subsections"]:
                    self._extract_comprehensive_metadata(subsection, metadata, organization_lookup)
        
        elif isinstance(section, list):
            for item in section:
                self._extract_comprehensive_metadata(item, metadata, organization_lookup)