# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

import os
import json
import toml
import yaml
import tarfile
import configparser
from typing import List


class Doc:
    _type = dict

    def __init__(self, source):
        self._source = source

    def __str__(self):
        return str(self._source)

    def load(self):
        """Load data from file of given format."""
        if not os.path.exists(self._source):
            return {}
        try:
            return self._load()
        except Exception as e:
            raise Exception('Unable to read file %s. %s' % (self._source, e))

    def dump(self, data):
        """Dump the anifest file to desired file or to the source."""
        dir_path = os.path.dirname(self._source)
        if len(dir_path) > 0 and not os.path.exists(dir_path):
            os.makedirs(dir_path)
        self._dump(data)


class Toml(Doc):
    """TOML document representation."""

    def __init__(self, file_path):
        Doc.__init__(self, file_path)

    def _load(self):
        with open(self._source, 'r') as f:
            return toml.load(f, dict)

    def _dump(self, data):
        with open(self._source, 'w') as f:
            toml.dump(data, f)


class Json(Doc):
    """JSON document representation."""

    def __init__(self, file_path):
        Doc.__init__(self, file_path)

    def _load(self):
        with open(self._source, 'r') as f:
            return json.load(f)

    def _dump(self, data):
        with open(self._source, 'w') as f:
            json.dump(data, f, indent=2)


class Yaml(Doc):
    """YAML document representation."""

    def __init__(self, file_path):
        Doc.__init__(self, file_path)

    def _load(self):
        with open(self._source, 'r') as f:
            return yaml.safe_load(f)

    def _dump(self, data):
        with open(self._source, 'w') as f:
            yaml.dump(data, f)


class Tar(Doc):
    """Tar file representation."""

    def __init__(self, file_path):
        Doc.__init__(self, file_path)

    def _dump(self, files: List):
        """
        Create a tar file at source path.

        :param files: Files and Directories to be Included in Tar File.
        :return: None
        """
        with tarfile.open(self._source, "w:gz") as tar:
            for each_file in files:
                tar.add(each_file, arcname=os.path.basename(each_file),
                        recursive=True)


class Ini(Doc):
    """Ini document representation."""

    def __init__(self, file_path):
        self._config = configparser.ConfigParser()
        Doc.__init__(self, file_path)
        self._type = configparser.SectionProxy

    def _load(self):
        self._config.read(self._source)
        return self._config

    def _dump(self, data):
        with open(self._source, 'w') as f:
            data.write(f)


class Dict(Doc):
    """Python dictionary representation as a document."""

    def __init__(self, data={}):
        Doc.__init__(self, data)

    def load(self):
        return self._source

    def dump(self, data):
        self._source = data


class Text(Doc):
    """Text document representation."""

    def __init__(self, file_path):
        Doc.__init__(self, file_path)

    def _load(self):
        """Load data from text file."""
        with open(self._source, 'r') as f:
            return f.read()

    def _dump(self, data):
        """Dump the data to desired file or to the source."""
        with open(self._source, 'w') as f:
            f.write(data)


class JsonMessage(Json):
    """Json respresentation as a document."""

    def __init__(self, json_str):
        """
        Represent the Json Without FIle.

        :param json_str: Json String to be processed.
        :type: str.
        """
        Json.__init__(self, json_str)

    def load(self):
        """
        Load the json to python interpretable Dictionary Object.

        :return: :type: Dict.
        """
        return json.loads(self._source)

    def dump(self, data):
        """
        Set the data _source after converting to json.

        :param data: :type: Dict
        :return:
        """
        self._source = json.dumps(data)
        return self._source


class Payload:
    """Payload in the specified format."""

    def __init__(self, doc):
        self._dirty = False
        self._doc = doc
        self.load()

    def load(self):
        if self._dirty:
            raise Exception('%s not synced to disk' % self._doc)
        self._data = self._doc.load()
        return self._data

    def dump(self):
        """Dump the anifest file to desired file or to the source."""
        self._doc.dump(self._data)
        self._dirty = False

    def _get(self, key, data):
        """Obtain value for the given key."""
        k = key.split('.', 1)
        if k[0] not in data.keys():
            return None
        return self._get(k[1], data[k[0]]) if len(k) > 1 else data[k[0]]

    def get(self, key):
        if self._data is None:
            raise Exception('Configuration %s not initialized' % self._doc)
        return self._get(key, self._data)

    def _set(self, key, val, data):
        k = key.split('.', 1)
        if len(k) == 1:
            data[k[0]] = val
            return
        if k[0] not in data.keys() or not isinstance(data[k[0]], self._doc._type):
            data[k[0]] = {}
        self._set(k[1], val, data[k[0]])

    def set(self, key, val):
        """Set the value into the DB for the given key."""
        self._set(key, val, self._data)
        self._dirty = True

    def pop(self, key, *defaultvalue):
        k = key.split('.', 1)
        if len(k) == 1:
            dirty = k[0] in self._data
            value = self._data.pop(k[0], *defaultvalue)
        else:
            dirty = k[1] in self._data[k[0]]
            value = self._data[k[0]].pop(k[1], *defaultvalue)
            if dirty and not bool(self._data[k[0]]):
                self._data.pop(k, None)
        self._dirty = dirty
        return value

    def convert(self, schema, payload):
        """
        Convert fist Schema to 2nd Schema depending on mapping dictionary.

        :param schema: mapping dictionary :type:Dict
        :param payload: Payload Class Object with desired Source.
        :return: :type: Dict
        Mapping file example -
        key <input schema> : value <output schema>
        """
        for key in schema.keys():
            val = self.get(key)
            payload.set(schema[key], val)
        return payload

    def data(self):
        return self._data


class CommonPayload:
    """Common payload representing Json, Toml, Yaml, Ini Doc."""

    def __init__(self, source):
        self._source = source
        # Mapping of file extensions and doc classes.
        self._MAP = {
            "json": Json, "toml": Toml, "yaml": Yaml,
            "ini": Ini, "yml": Yaml, "txt": Text
        }
        self._doc = self.get_doc_type()

    def get_doc_type(self):
        """Get mapped doc class object bases on file extension."""
        try:
            extension = os.path.splitext(self._source)[1][1:].strip().lower()
            doc_obj = self._MAP[extension]
            return doc_obj(self._source)
        except KeyError as error:
            raise KeyError(f"Unsupported file type:{error}")
        except Exception as e:
            raise Exception(f"Unable to read file {self._source}. {e}")

    def load(self):
        """Load data from file of given format."""
        return self._doc._load()

    def dump(self, data):
        """Dump the data to desired file or to the source."""
        self._doc._dump(data)
