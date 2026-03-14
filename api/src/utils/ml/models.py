from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd
from sdv.single_table import CTGANSynthesizer, TVAESynthesizer, GaussianCopulaSynthesizer
from sdv.metadata import SingleTableMetadata

class GenerativeModel(ABC):
    @abstractmethod
    def train(self, data: pd.DataFrame):
        pass
    
    @abstractmethod
    def generate(self, num_rows: int) -> pd.DataFrame:
        pass

class CTGANModel(GenerativeModel):
    def __init__(self):
        self.model = None
        self.metadata = SingleTableMetadata()

    def train(self, data: pd.DataFrame):
        self.metadata.detect_from_dataframe(data)
        self.model = CTGANSynthesizer(self.metadata)
        self.model.fit(data)

    def generate(self, num_rows: int) -> pd.DataFrame:
        if self.model is None:
            raise ValueError("Model must be trained before generation.")
        return self.model.sample(num_rows)

class VAEModel(GenerativeModel):
    def __init__(self):
        self.model = None
        self.metadata = SingleTableMetadata()

    def train(self, data: pd.DataFrame):
        self.metadata.detect_from_dataframe(data)
        self.model = TVAESynthesizer(self.metadata)
        self.model.fit(data)

    def generate(self, num_rows: int) -> pd.DataFrame:
        if self.model is None:
            raise ValueError("Model must be trained before generation.")
        return self.model.sample(num_rows)

class CopulaModel(GenerativeModel):
    def __init__(self):
        self.model = None
        self.metadata = SingleTableMetadata()

    def train(self, data: pd.DataFrame):
        self.metadata.detect_from_dataframe(data)
        self.model = GaussianCopulaSynthesizer(self.metadata)
        self.model.fit(data)

    def generate(self, num_rows: int) -> pd.DataFrame:
        if self.model is None:
            raise ValueError("Model must be trained before generation.")
        return self.model.sample(num_rows)

class ModelRegistry:
    def __init__(self):
        self.models = {
            "ctgan": CTGANModel,
            "vae": VAEModel,
            "copula": CopulaModel
        }
        
    def get_model(self, model_type: str) -> GenerativeModel:
        model_cls = self.models.get(model_type.lower(), CopulaModel)
        return model_cls()

    def select_best_model(self, data: pd.DataFrame) -> str:
        """Heuristic-based model selection."""
        if len(data.columns) > 15:
            return "ctgan"
        if data.select_dtypes(include=['object']).shape[1] > 5:
            return "vae"
        return "copula"
