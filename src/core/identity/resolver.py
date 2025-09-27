"""Identity resolution for linking customer touchpoints."""

from typing import List, Dict, Any
import pandas as pd
from ...models.enums import LinkingMethod
from ...models.touchpoint import Touchpoint


def select_linking_method(df: pd.DataFrame) -> LinkingMethod:
    """Select the best linking method based on data quality."""
    if 'customer_id' in df.columns and df['customer_id'].notna().mean() > 0.8:
        return LinkingMethod.CUSTOMER_ID
    elif 'session_id' in df.columns and 'email' in df.columns:
        return LinkingMethod.SESSION_EMAIL
    elif 'email' in df.columns:
        return LinkingMethod.EMAIL_ONLY
    else:
        return LinkingMethod.AGGREGATE


class IdentityResolver:
    """Resolves customer identity across touchpoints."""
    
    def __init__(self, linking_method: LinkingMethod):
        self.linking_method = linking_method
    
    def resolve_identities(self, df: pd.DataFrame) -> Dict[str, List[int]]:
        """Resolve customer identities and return mapping of identity to row indices."""
        identity_map = {}
        
        if self.linking_method == LinkingMethod.CUSTOMER_ID:
            identity_map = self._resolve_by_customer_id(df)
        elif self.linking_method == LinkingMethod.SESSION_EMAIL:
            identity_map = self._resolve_by_session_email(df)
        elif self.linking_method == LinkingMethod.EMAIL_ONLY:
            identity_map = self._resolve_by_email(df)
        else:  # AGGREGATE
            identity_map = self._resolve_aggregate(df)
        
        return identity_map
    
    def _resolve_by_customer_id(self, df: pd.DataFrame) -> Dict[str, List[int]]:
        """Resolve identities using customer_id."""
        identity_map = {}
        
        for idx, row in df.iterrows():
            customer_id = str(row.get('customer_id', ''))
            if customer_id and customer_id != 'nan':
                if customer_id not in identity_map:
                    identity_map[customer_id] = []
                identity_map[customer_id].append(idx)
        
        return identity_map
    
    def _resolve_by_session_email(self, df: pd.DataFrame) -> Dict[str, List[int]]:
        """Resolve identities using session_id and email combination."""
        identity_map = {}
        
        for idx, row in df.iterrows():
            session_id = str(row.get('session_id', ''))
            email = str(row.get('email', ''))
            
            # Create composite key
            identity_key = f"{session_id}:{email}"
            if session_id != 'nan' or email != 'nan':
                if identity_key not in identity_map:
                    identity_map[identity_key] = []
                identity_map[identity_key].append(idx)
        
        return identity_map
    
    def _resolve_by_email(self, df: pd.DataFrame) -> Dict[str, List[int]]:
        """Resolve identities using email only."""
        identity_map = {}
        
        for idx, row in df.iterrows():
            email = str(row.get('email', ''))
            if email and email != 'nan':
                if email not in identity_map:
                    identity_map[email] = []
                identity_map[email].append(idx)
        
        return identity_map
    
    def _resolve_aggregate(self, df: pd.DataFrame) -> Dict[str, List[int]]:
        """Aggregate all data without identity resolution."""
        return {"aggregate": list(df.index)}
