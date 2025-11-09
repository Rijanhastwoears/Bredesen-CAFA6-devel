#!/usr/bin/env python3
"""
Protein Ontology and Annotation Framework (POAF)
A program to interact with protein OBOs and protein annotations.

This tool downloads and manages protein ontology (OBO) and protein 
annotation (PAF) files, providing an interactive interface for querying.
"""

import os
import hashlib
import requests
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import argparse


class ProteinDataManager:
    """Manages protein ontology and annotation data with versioning."""
    
    def __init__(self, data_dir: str = ".PRO"):
        """Initialize the data manager.
        
        Args:
            data_dir: Directory to store protein data files
        """
        self.data_dir = data_dir
        self.obo_url = "http://purl.obolibrary.org/obo/pr.obo"
        self.paf_url = "https://proconsortium.org/download/current/PAF.txt"
        self.obo_file = os.path.join(data_dir, "protein_ontology.obo")
        self.paf_file = os.path.join(data_dir, "protein_annotations.paf")
        self.version_file = os.path.join(data_dir, "versions.json")
        
    def setup_data_directory(self) -> None:
        """Create .PRO directory if it doesn't exist."""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            print(f"Created directory: {self.data_dir}")
        else:
            print(f"Using existing directory: {self.data_dir}")
    
    def calculate_file_hash(self, file_path: str) -> Optional[str]:
        """Calculate SHA-256 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Hexadecimal hash string or None if file doesn't exist
        """
        if not os.path.exists(file_path):
            return None
            
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            print(f"Error calculating hash for {file_path}: {e}")
            return None
    
    def load_version_info(self) -> Dict[str, str]:
        """Load version information from JSON file.
        
        Returns:
            Dictionary mapping file names to their hashes
        """
        if not os.path.exists(self.version_file):
            return {}
            
        try:
            with open(self.version_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading version info: {e}")
            return {}
    
    def save_version_info(self, version_info: Dict[str, str]) -> None:
        """Save version information to JSON file.
        
        Args:
            version_info: Dictionary mapping file names to their hashes
        """
        try:
            with open(self.version_file, 'w') as f:
                json.dump(version_info, f, indent=2)
        except Exception as e:
            print(f"Error saving version info: {e}")
    
    def download_file(self, url: str, local_path: str) -> bool:
        """Download a file from URL to local path.
        
        Args:
            url: URL to download from
            local_path: Local path to save to
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            print(f"Downloading {url}...")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"Downloaded to: {local_path}")
            return True
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return False
    
    def update_data(self) -> bool:
        """Update data files if needed based on hash comparison.
        
        Returns:
            True if update successful or no update needed, False otherwise
        """
        self.setup_data_directory()
        
        version_info = self.load_version_info()
        current_time = datetime.now().isoformat()
        
        # Check OBO file
        obo_hash = self.calculate_file_hash(self.obo_file)
        if obo_hash != version_info.get("obo_hash"):
            print("OBO file needs update or doesn't exist")
            if self.download_file(self.obo_url, self.obo_file):
                new_obo_hash = self.calculate_file_hash(self.obo_file)
                version_info["obo_hash"] = new_obo_hash
                version_info["obo_last_updated"] = current_time
            else:
                return False
        
        # Check PAF file
        paf_hash = self.calculate_file_hash(self.paf_file)
        if paf_hash != version_info.get("paf_hash"):
            print("PAF file needs update or doesn't exist")
            if self.download_file(self.paf_url, self.paf_file):
                new_paf_hash = self.calculate_file_hash(self.paf_file)
                version_info["paf_hash"] = new_paf_hash
                version_info["paf_last_updated"] = current_time
            else:
                return False
        
        # Save updated version info
        self.save_version_info(version_info)
        
        print("Data files are up to date")
        return True


class ProteinDataParser:
    """Parses OBO and PAF files for querying."""
    
    def __init__(self, data_manager: ProteinDataManager):
        """Initialize the parser.
        
        Args:
            data_manager: ProteinDataManager instance
        """
        self.data_manager = data_manager
        self.obo_data = {}
        self.paf_data = []
        
    def load_obo_data(self) -> bool:
        """Load and parse OBO ontology data.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.data_manager.obo_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse OBO format - simplified parsing
            current_term = {}
            for line in content.split('\n'):
                line = line.strip()
                if line == '[Term]':
                    if current_term and 'id' in current_term:
                        # Ensure term ID is a string and all values are hashable
                        term_id = str(current_term['id'])
                        clean_term = {}
                        for k, v in current_term.items():
                            if isinstance(v, list):
                                clean_term[k] = [str(x) for x in v]
                            else:
                                clean_term[k] = str(v)
                        self.obo_data[term_id] = clean_term
                    current_term = {}
                elif ':' in line and current_term is not None:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    if key in current_term:
                        if not isinstance(current_term[key], list):
                            current_term[key] = [current_term[key]]
                        current_term[key].append(value)
                    else:
                        current_term[key] = value
            
            # Add the last term
            if current_term and 'id' in current_term:
                # Ensure term ID is a string and all values are hashable
                term_id = str(current_term['id'])
                clean_term = {}
                for k, v in current_term.items():
                    if isinstance(v, list):
                        clean_term[k] = [str(x) for x in v]
                    else:
                        clean_term[k] = str(v)
                self.obo_data[term_id] = clean_term
                
            print(f"Loaded {len(self.obo_data)} terms from OBO file")
            return True
            
        except Exception as e:
            print(f"Error loading OBO data: {e}")
            return False
    
    def load_paf_data(self) -> bool:
        """Load and parse PAF annotation data.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.data_manager.paf_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if not lines:
                print("PAF file is empty")
                return False
            
            # Parse PAF format - tab-separated with header
            header = lines[0].strip().split('\t')
            print(f"PAF header: {header}")
            
            for line_num, line in enumerate(lines[1:], 2):  # Start from line 2
                if line.strip() and not line.startswith('#'):
                    parts = line.strip().split('\t')
                    if len(parts) >= len(header):  # Ensure we have all columns
                        paf_entry = {
                            'line_number': line_num,
                            'raw_line': line.strip(),
                            'fields': parts,
                            'header': header
                        }
                        # Create a dictionary mapping header names to values
                        entry_dict = {}
                        for i, col_name in enumerate(header):
                            if i < len(parts):
                                entry_dict[col_name] = parts[i]
                        paf_entry['data'] = entry_dict
                        self.paf_data.append(paf_entry)
            
            print(f"Loaded {len(self.paf_data)} entries from PAF file")
            return True
            
        except Exception as e:
            print(f"Error loading PAF data: {e}")
            return False
    
    def search_obo_terms(self, query: str, search_fields: List[str] = None) -> List[Dict]:
        """Search OBO terms by query.
        
        Args:
            query: Search query string
            search_fields: Fields to search in (default: ['id', 'name', 'def'])
            
        Returns:
            List of matching terms
        """
        if not self.obo_data:
            return []
            
        if search_fields is None:
            search_fields = ['id', 'name', 'def']
        
        results = []
        query_lower = query.lower()
        
        for term_id, term_data in self.obo_data.items():
            for field in search_fields:
                if field in term_data:
                    field_value = term_data[field]
                    if isinstance(field_value, list):
                        field_value_str = ' '.join(str(v) for v in field_value)
                    else:
                        field_value_str = str(field_value)
                    
                    if field_value_str and query_lower in field_value_str.lower():
                        results.append({
                            'id': term_id,
                            'name': term_data.get('name', 'N/A'),
                            'definition': term_data.get('def', 'N/A'),
                            'matched_field': field
                        })
                        break
        
        return results
    
    def search_paf_annotations(self, query: str) -> List[Dict]:
        """Search PAF annotations by query.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching annotations
        """
        if not self.paf_data:
            return []
            
        results = []
        query_lower = query.lower()
        
        for entry in self.paf_data:
            # Search in all fields
            match_found = False
            for field_name, field_value in entry['data'].items():
                if field_value and query_lower in field_value.lower():
                    match_found = True
                    break
            
            if match_found:
                results.append({
                    'line_number': entry['line_number'],
                    'data': entry['data'],
                    'protein_id': entry['data'].get('PRO_ID', 'N/A'),
                    'annotation': entry['data'].get('Object_term', 'N/A')
                })
        
        return results
    
    def get_term_details(self, term_id: str) -> Optional[Dict]:
        """Get detailed information for a specific term.
        
        Args:
            term_id: Term identifier
            
        Returns:
            Term data dictionary or None if not found
        """
        return self.obo_data.get(term_id)
    
    def get_annotations_for_protein(self, protein_id: str) -> List[Dict]:
        """Get all annotations for a specific protein.
        
        Args:
            protein_id: Protein identifier
            
        Returns:
            List of annotation entries
        """
        results = []
        for entry in self.paf_data:
            if entry['data'].get('PRO_ID') == protein_id:
                results.append({
                    'line_number': entry['line_number'],
                    'protein_id': entry['data'].get('PRO_ID', 'N/A'),
                    'annotation': entry['data'].get('Object_term', 'N/A'),
                    'full_data': entry['data'],
                    'ontology_id': entry['data'].get('Ontology_ID', 'N/A'),
                    'ontology_term': entry['data'].get('Ontology_term', 'N/A'),
                    'relation': entry['data'].get('Relation', 'N/A')
                })
        return results


class InteractiveProteinTool:
    """Interactive command-line interface for protein data querying."""
    
    def __init__(self):
        """Initialize the interactive tool."""
        self.data_manager = ProteinDataManager()
        self.parser = ProteinDataParser(self.data_manager)
        
    def setup(self) -> bool:
        """Setup the tool by downloading and loading data.
        
        Returns:
            True if setup successful, False otherwise
        """
        print("=== Protein Ontology and Annotation Framework (POAF) ===")
        print("Setting up data files...")
        
        if not self.data_manager.update_data():
            print("Failed to update data files")
            return False
        
        print("Loading data into memory...")
        if not self.parser.load_obo_data():
            print("Failed to load OBO data")
            return False
            
        if not self.parser.load_paf_data():
            print("Failed to load PAF data")
            return False
            
        print("Setup complete!")
        return True
    
    def search_menu(self):
        """Display search options and handle user input."""
        while True:
            print("\n=== Search Options ===")
            print("1. Search OBO terms")
            print("2. Search PAF annotations")
            print("3. Get term details by ID")
            print("4. Get annotations for protein")
            print("5. Show statistics")
            print("6. Exit")
            
            choice = input("\nEnter your choice (1-6): ").strip()
            
            if choice == '1':
                self.search_obo_terms()
            elif choice == '2':
                self.search_paf_annotations()
            elif choice == '3':
                self.get_term_details()
            elif choice == '4':
                self.get_protein_annotations()
            elif choice == '5':
                self.show_statistics()
            elif choice == '6':
                print("Thank you for using POAF!")
                break
            else:
                print("Invalid choice. Please try again.")
    
    def search_obo_terms(self):
        """Handle OBO term search."""
        query = input("Enter search term: ").strip()
        if not query:
            print("Search term cannot be empty")
            return
        
        print(f"\nSearching OBO terms for: '{query}'")
        results = self.parser.search_obo_terms(query)
        
        if not results:
            print("No results found")
        else:
            print(f"\nFound {len(results)} results:")
            for i, result in enumerate(results[:10], 1):  # Show first 10 results
                print(f"{i}. ID: {result['id']}")
                print(f"   Name: {result['name']}")
                print(f"   Matched field: {result['matched_field']}")
                if i >= 10:
                    remaining = len(results) - 10
                    if remaining > 0:
                        print(f"   ... and {remaining} more results")
                    break
            print()
    
    def search_paf_annotations(self):
        """Handle PAF annotation search."""
        query = input("Enter search term: ").strip()
        if not query:
            print("Search term cannot be empty")
            return
        
        print(f"\nSearching PAF annotations for: '{query}'")
        results = self.parser.search_paf_annotations(query)
        
        if not results:
            print("No results found")
        else:
            print(f"\nFound {len(results)} results:")
            for i, result in enumerate(results[:10], 1):  # Show first 10 results
                print(f"{i}. Line {result['line_number']}: {result['protein_id']}")
                print(f"   Term: {result['annotation']}")
                print(f"   Ontology: {result['data'].get('Ontology_term', 'N/A')}")
                if i >= 10:
                    remaining = len(results) - 10
                    if remaining > 0:
                        print(f"   ... and {remaining} more results")
                    break
            print()
    
    def get_term_details(self):
        """Handle detailed term lookup."""
        term_id = input("Enter term ID: ").strip()
        if not term_id:
            print("Term ID cannot be empty")
            return
        
        print(f"\nGetting details for term: {term_id}")
        term_data = self.parser.get_term_details(term_id)
        
        if not term_data:
            print("Term not found")
        else:
            print(f"\nTerm Details:")
            for key, value in term_data.items():
                if isinstance(value, list):
                    print(f"{key}: {'; '.join(value)}")
                else:
                    print(f"{key}: {value}")
            print()
    
    def get_protein_annotations(self):
        """Handle protein annotation lookup."""
        protein_id = input("Enter protein ID: ").strip()
        if not protein_id:
            print("Protein ID cannot be empty")
            return
        
        print(f"\nGetting annotations for protein: {protein_id}")
        annotations = self.parser.get_annotations_for_protein(protein_id)
        
        if not annotations:
            print("No annotations found for this protein")
        else:
            print(f"\nFound {len(annotations)} annotations:")
            for i, annotation in enumerate(annotations, 1):
                print(f"{i}. Line {annotation['line_number']}: {annotation['annotation']}")
                print(f"   Ontology ID: {annotation['ontology_id']}")
                print(f"   Ontology Term: {annotation['ontology_term']}")
                print(f"   Relation: {annotation['relation']}")
                if i >= 10:
                    remaining = len(annotations) - 10
                    if remaining > 0:
                        print(f"   ... and {remaining} more annotations")
                    break
            print()
    
    def show_statistics(self):
        """Display dataset statistics."""
        print(f"\n=== Dataset Statistics ===")
        print(f"OBO terms loaded: {len(self.parser.obo_data)}")
        print(f"PAF annotations loaded: {len(self.parser.paf_data)}")
        print(f"Data directory: {self.data_manager.data_dir}")
        print(f"OBO file: {self.data_manager.obo_file}")
        print(f"PAF file: {self.data_manager.paf_file}")
        
        version_info = self.data_manager.load_version_info()
        if version_info:
            print(f"\nLast updates:")
            print(f"OBO: {version_info.get('obo_last_updated', 'Unknown')}")
            print(f"PAF: {version_info.get('paf_last_updated', 'Unknown')}")
        print()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Protein Ontology and Annotation Framework")
    parser.add_argument('--update-only', action='store_true', 
                       help='Only update data files without starting interactive mode')
    
    args = parser.parse_args()
    
    tool = InteractiveProteinTool()
    
    # Setup data
    if not tool.setup():
        print("Setup failed. Exiting.")
        return 1
    
    if args.update_only:
        print("Data update complete.")
        return 0
    
    # Start interactive mode
    try:
        tool.search_menu()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())