import { useEffect, useCallback } from 'react';
import { stateManager } from '../utils/stateManager';
import type { AppState } from '../utils/stateManager';

export interface SessionRecoveryOptions {
  onRecoverSession: (state: Partial<AppState>) => void;
  onRecoverResults: () => void;
  onShowRecoveryDialog: () => void;
}

export function useSessionRecovery({
  onRecoverSession,
  onRecoverResults,
  onShowRecoveryDialog,
}: SessionRecoveryOptions) {
  
  // Check for session recovery on mount
  useEffect(() => {
    const sessionState = stateManager.getSessionState();
    const appState = stateManager.getAppState();
    
    if (sessionState) {
      // We have a recent session to recover
      console.log('Session recovery available:', sessionState);
      
      // Check what type of recovery is needed
      if (sessionState.results) {
        // We have results to show
        onRecoverResults();
      } else if (sessionState.selectedFile || sessionState.activeStep > 0) {
        // We have a workflow in progress
        onRecoverSession(sessionState);
      }
    } else if (appState.results || appState.analysisHistory.length > 0) {
      // We have persistent data but no recent session
      onShowRecoveryDialog();
    }
  }, [onRecoverSession, onRecoverResults, onShowRecoveryDialog]);

  // Auto-save session state
  const saveSessionState = useCallback((state: Partial<AppState>) => {
    stateManager.saveSessionState(state);
  }, []);

  // Clear session state when workflow is complete
  const clearSessionState = useCallback(() => {
    stateManager.clearSessionState();
  }, []);

  // Check if there's recoverable session data
  const hasRecoverableSession = useCallback(() => {
    return !!stateManager.getSessionState();
  }, []);

  return {
    saveSessionState,
    clearSessionState,
    hasRecoverableSession,
  };
}

export default useSessionRecovery;
