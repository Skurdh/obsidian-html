import os
import yaml
import json

from pathlib import Path

from ...core.FileObject import FileObject
from ...parser.MarkdownPage import MarkdownPage

from ..base_classes import ObsidianHtmlModule


class FilterOnMetadataModule(ObsidianHtmlModule):
    """
    This module will try to read the metadata of each markdown file in the `index/files.json` list.
    If this succeeds it will check whether the required keys are present/absent
    Any files that do not have the required keys/have keys that should be absent will be filtered out.
    You can configure whether failure to load the metadata should lead to the file being filtered out or not.
    """

    @property
    def requires(self):
        return tuple(["index/markdown_files.json", "index/files.json", "index/metadata.json", "paths.json"])

    @property
    def provides(self):
        return tuple(["index/files.json", "index/markdown_files.json", "excluded_files_by_metadata.json",])

    @property
    def alters(self):
        return tuple()

    def define_mod_config_defaults(self):
        self.mod_config["include_on"] = {
            "value": [],
            "description": [
                "Attributes to match on, will be applied if value != []",
                "You can currently use: {'tagged': 'tag_name'}",
                "First list is a list of lists that are ORed, so any list can give true and this will match",
                "The dict elements in the sublists are ANDed together, so every element needs to give true",
            ],
            "example_value": [
                [
                    {"tagged": "type/automation"}
                ],
            ],
        }
        self.mod_config["exclude_on"] = {
            "value": [],
            "description": [
                "Works the same as 'include_on', but in reverse.",
                "Include_on results in an 'excluded_files' list, as does this setting. Both lists are summed.",
            ],
            "example_value": [
                [
                    {"tagged": "type/automation"}
                ],
            ],

        }

    def accept(self, module_data_folder):
        """This function is run before run(), if it returns False, then the module run is skipped entirely. Any other value will be accepted"""
        return


    def test_requirement(self, element, metadata):
        if "tagged" in element.keys():
            tag_name = element["tagged"]
            return (tag_name in metadata["tags"])
        else:
            raise Exception(f'element {element} is not recognized as a valid selector')
        return False

    def test_publish(self, rel_path, metadata, include_on):
        if len(include_on) == 0:
            return True
        
        for and_list in include_on:
            publish = True
            for element in and_list:
                # when ever a test fails, publish will toggle permanently to false
                publish = publish and self.test_requirement(element, metadata)

            # if one and_list is true, this means that the result is already known
            # as all and_lists are orred together, so exit early
            if publish:
                return True

        return False

    def test_exclude(self, rel_path, metadata, exclude_on):
        if len(exclude_on) == 0:
            return False
        
        for and_list in exclude_on:
            exclude = True
            for element in and_list:
                # when ever a test fails, exclude will toggle permanently to false
                exclude = exclude and self.test_requirement(element, metadata)

            # if one and_list is true, this means that the result is already known
            # as all and_lists are orred together, so exit early
            if exclude:
                return True

        return False

    def run(self):
        # get input
        paths = self.modfile("paths.json").read().from_json()

        md_files = self.modfile("index/markdown_files.json").read().from_json()
        metadata_dict = self.modfile("index/metadata.json").read().from_json()

        include_on = self.value_of("include_on")
        exclude_on = self.value_of("exclude_on")
        
        # judge each file
        exclude_list = []
        for file in md_files:
            rel_path = Path(file).relative_to(paths["input_folder"]).as_posix()
            metadata = metadata_dict[rel_path]

            # test whether include_on says to publish the file
            publish = self.test_publish(rel_path, metadata, include_on)
            if publish is False:
                exclude_list.append(file)

            # test whether exclude_on says to exclude the file
            exclude = self.test_exclude(rel_path, metadata, exclude_on)
            if exclude:
                exclude_list.append(file)

        # remove duplicates
        exclude_list = list(set(exclude_list))

        # check that the entrypoint file is not being filtered out
        if paths["entrypoint"] in exclude_list:
           self.print('ERROR', f'You have configured {self.nametag} to filter out {paths["entrypoint"]}, which is your entrypoint. Correct this and run again.')
           exit(1)
        
        # update file lists
        new_md_files = [x for x in md_files if x not in exclude_list]
        self.modfile("index/markdown_files.json", new_md_files).to_json().write()
            
        files = self.modfile("index/files.json").read().from_json()
        new_files = [x for x in files if (x not in exclude_list)]
        self.modfile("index/files.json", new_files).to_json().write()

        # record the files that were excluded
        self.modfile("excluded_files_by_metadata.json", exclude_list).to_json().write()
        

    def integrate_load(self, pb):
        """Used to integrate a module with the current flow, to become deprecated when all elements use modular structure"""
        pass

    def integrate_save(self, pb):
        """Used to integrate a module with the current flow, to become deprecated when all elements use modular structure"""
        pass