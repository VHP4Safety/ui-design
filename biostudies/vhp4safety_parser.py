"""
VHP4Safety-specific parser for BioStudies metadata
This module extracts and organizes BioStudies data into VHP4Safety display modules
"""

class VHP4SafetyParser:
    """Parser for organizing BioStudies metadata into VHP4Safety modules"""
    
    def __init__(self):
        pass
    
    def parse_to_modules(self, raw_data):
        """
        Parse BioStudies JSON into VHP4Safety display modules
        
        Args:
            raw_data (dict): Raw JSON response from BioStudies API
            
        Returns:
            dict: Organized metadata with the following modules:
                - general_info
                - author_info
                - chemical_info
                - biological_model_info
                - exposure_info
                - endpoint_readout_info
                - files
        """
        print(f"[VHP4Safety Parser] Parsing study: {raw_data.get('accno', 'Unknown')}")
        
        modules = {
            "general_info": {},
            "author_info": [],
            "chemical_info": {
                "test_chemicals": [],
                "positive_controls": []
            },
            "biological_model_info": {
                "cell_lines": []
            },
            "exposure_info": [],
            "endpoint_readout_info": {},
            "files": []
        }
        
        # Build organization lookup for author affiliations
        org_lookup = {}
        if "section" in raw_data:
            self._build_organization_lookup(raw_data["section"], org_lookup)
        
        # Extract general information
        self._extract_general_info(raw_data, modules)
        
        # Extract module-specific data from sections
        if "section" in raw_data:
            self._extract_modules_from_section(raw_data["section"], modules, org_lookup)
        
        # Extract files
        if "section" in raw_data:
            self._extract_files(raw_data["section"], modules)
        
        # Debug output
        print(f"[VHP4Safety Parser] Extracted modules:")
        print(f"  - Authors: {len(modules['author_info'])} found")
        print(f"  - Chemicals: {len(modules['chemical_info']['test_chemicals'])} test, {len(modules['chemical_info']['positive_controls'])} controls")
        print(f"  - Cell lines: {len(modules['biological_model_info']['cell_lines'])} found")
        print(f"  - Exposure info: {len(modules['exposure_info'])} entries")
        print(f"  - Files: {len(modules['files'])} found")
        
        return modules
    
    def _extract_general_info(self, raw_data, modules):
        """Extract general information module"""
        # Basic fields
        modules["general_info"]["accession"] = raw_data.get("accno", "N/A")
        modules["general_info"]["title"] = raw_data.get("title", "N/A")
        modules["general_info"]["release_date"] = raw_data.get("rdate", "N/A")
        modules["general_info"]["type"] = raw_data.get("type", "N/A")
        
        # Extract from section attributes
        if "section" in raw_data and "attributes" in raw_data["section"]:
            for attr in raw_data["section"]["attributes"]:
                attr_name = attr.get("name", "")
                attr_value = attr.get("value", "")
                attr_name_lower = attr_name.lower()
                
                # Store specific fields with their qualifiers
                if attr_name_lower in ["title", "releasedate", "description", "organism", 
                                       "license", "bioassay", "organ", "tissue",
                                       "adverse outcome pathway", "aop event", "case study",
                                       "flow step", "regulatory questions"]:
                    modules["general_info"][attr_name] = {
                        "value": attr_value,
                        "valqual": attr.get("valqual", [])
                    }
        
        # Extract links from section
        if "section" in raw_data and "links" in raw_data["section"]:
            modules["general_info"]["links"] = []
            for link in raw_data["section"]["links"]:
                link_info = {"url": link.get("url", "")}
                if "attributes" in link:
                    for attr in link["attributes"]:
                        if attr.get("name") == "Description":
                            link_info["description"] = attr.get("value", "")
                modules["general_info"]["links"].append(link_info)
    
    def _extract_modules_from_section(self, section, modules, org_lookup):
        """Extract module data from section and subsections"""
        if isinstance(section, dict):
            # Process subsections
            if "subsections" in section:
                for subsection in section["subsections"]:
                    self._process_subsection(subsection, modules, org_lookup)
        
        elif isinstance(section, list):
            for item in section:
                self._extract_modules_from_section(item, modules, org_lookup)
    
    def _process_subsection(self, subsection, modules, org_lookup):
        """Process individual subsection based on type"""
        if isinstance(subsection, list):
            # Handle arrays of subsections
            for item in subsection:
                if isinstance(item, dict):
                    self._process_subsection(item, modules, org_lookup)
        
        elif isinstance(subsection, dict):
            section_type = subsection.get("type", "").lower()
            
            # Author information
            if section_type in ["author", "contact", "person"]:
                author_data = self._extract_author(subsection, org_lookup)
                if author_data:
                    modules["author_info"].append(author_data)
            
            # Chemical information
            elif section_type == "chemicals":
                chemical = self._extract_attributes(subsection)
                if chemical:
                    modules["chemical_info"]["test_chemicals"].append(chemical)
            
            # Positive controls
            elif section_type == "positive controls":
                control = self._extract_attributes(subsection)
                if control:
                    modules["chemical_info"]["positive_controls"].append(control)
            
            # Biological model information
            elif section_type == "cell lines":
                cell_line = self._extract_attributes(subsection)
                if cell_line:
                    modules["biological_model_info"]["cell_lines"].append(cell_line)
            
            # Exposure information
            elif section_type == "experimental design":
                exp_design = self._extract_attributes(subsection)
                if exp_design:
                    modules["exposure_info"].append(exp_design)
            
            # Endpoint readout information
            elif section_type == "assay details":
                assay_details = self._extract_attributes(subsection)
                modules["endpoint_readout_info"].update(assay_details)
            
            # Funding information (add to general info)
            elif section_type == "funding":
                funding = self._extract_attributes(subsection)
                if funding:
                    if "funding" not in modules["general_info"]:
                        modules["general_info"]["funding"] = []
                    modules["general_info"]["funding"].append(funding)
            
            # Process nested subsections
            if "subsections" in subsection:
                for nested in subsection["subsections"]:
                    self._process_subsection(nested, modules, org_lookup)
    
    def _extract_author(self, subsection, org_lookup):
        """Extract author information with affiliation resolution"""
        if "attributes" not in subsection:
            return None
        
        author_data = {}
        affiliation_ref = None
        
        for attr in subsection["attributes"]:
            attr_name = attr.get("name", "")
            attr_value = attr.get("value", "")
            
            if attr.get("reference") and attr_name.lower() == "affiliation":
                affiliation_ref = attr_value
            else:
                author_data[attr_name] = attr_value
        
        # Resolve affiliation
        if affiliation_ref and affiliation_ref in org_lookup:
            author_data["affiliation_resolved"] = org_lookup[affiliation_ref].get("name", "")
        
        return author_data if author_data else None
    
    def _extract_attributes(self, subsection):
        """Extract all attributes from a subsection into a dict"""
        if "attributes" not in subsection:
            return {}
        
        data = {}
        for attr in subsection["attributes"]:
            data[attr.get("name", "")] = attr.get("value", "")
        
        return data
    
    def _build_organization_lookup(self, section, org_lookup):
        """Build lookup table for organization references"""
        if isinstance(section, dict):
            if section.get("type", "").lower() in ["organization", "organisation"]:
                org_id = section.get("accno", "")
                if org_id and "attributes" in section:
                    org_data = {}
                    for attr in section["attributes"]:
                        attr_name = attr.get("name", "").lower()
                        if attr_name == "name":
                            org_data["name"] = attr.get("value", "")
                    if org_data:
                        org_lookup[org_id] = org_data
            
            if "subsections" in section:
                for subsection in section["subsections"]:
                    self._build_organization_lookup(subsection, org_lookup)
        
        elif isinstance(section, list):
            for item in section:
                self._build_organization_lookup(item, org_lookup)
    
    def _extract_files(self, section, modules):
        """Extract file information"""
        if isinstance(section, dict):
            if "files" in section:
                for file_info in section["files"]:
                    modules["files"].append({
                        "name": file_info.get("name", ""),
                        "size": file_info.get("size", ""),
                        "type": file_info.get("type", ""),
                        "path": file_info.get("path", "")
                    })
            
            if "subsections" in section:
                for subsection in section["subsections"]:
                    self._extract_files(subsection, modules)
        
        elif isinstance(section, list):
            for item in section:
                self._extract_files(item, modules)
