# api/src/utils/ml/registry.py

import abc
from typing import Dict, Any, Type, List
import pandas as pd
import pyarrow as pa
from ctgan import CTGAN
from sdv.single_table import TVAESynthesizer, GaussianCopulaSynthesizer

class GeneratorPlugin(abc.ABC):
    @abc.abstractmethod
    def fit(self, data: pd.DataFrame, parameters: Dict[str, Any]):
        pass

    @abc.abstractmethod
    def generate(self, n_rows: int) -> pd.DataFrame:
        pass

class CTGANPlugin(GeneratorPlugin):
    def __init__(self):
        self.model = None

    def fit(self, data: pd.DataFrame, parameters: Dict[str, Any]):
        epochs = parameters.get("epochs", 300)
        batch_size = parameters.get("batch_size", 500)
        self.model = CTGAN(epochs=epochs, batch_size=batch_size)
        self.model.fit(data)

    def generate(self, n_rows: int) -> pd.DataFrame:
        return self.model.sample(n_rows)

class TVAEPlugin(GeneratorPlugin):
    def __init__(self):
        self.model = None

    def fit(self, data: pd.DataFrame, parameters: Dict[str, Any]):
        from sdv.metadata import SingleTableMetadata
        metadata = SingleTableMetadata()
        metadata.detect_from_dataframe(data)
        self.model = TVAESynthesizer(metadata)
        self.model.fit(data)

    def generate(self, n_rows: int) -> pd.DataFrame:
        return self.model.sample(n_rows)

class CopulaPlugin(GeneratorPlugin):
    def __init__(self):
        self.model = None

    def fit(self, data: pd.DataFrame, parameters: Dict[str, Any]):
        from sdv.metadata import SingleTableMetadata
        metadata = SingleTableMetadata()
        metadata.detect_from_dataframe(data)
        self.model = GaussianCopulaSynthesizer(metadata)
        self.model.fit(data)

    def generate(self, n_rows: int) -> pd.DataFrame:
        return self.model.sample(n_rows)

class ModelRegistry:
    _plugins: Dict[str, Type[GeneratorPlugin]] = {
        "ctgan": CTGANPlugin,
        "vae": TVAEPlugin,
        "copula": CopulaPlugin
    }

    @classmethod
    def get_plugin(cls, name: str) -> GeneratorPlugin:
        plugin_class = cls._plugins.get(name.lower())
        if not plugin_class:
            raise ValueError(f"Plugin {name} not found")
        return plugin_class()

    @classmethod
    def list_plugins(cls) -> List[str]:
        return list(cls._plugins.keys())
