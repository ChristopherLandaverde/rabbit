# State Management & Persistence Guide

This guide explains how to refresh and remember state in your Rabbit MVP application.

## 🚀 Quick Start

Your application now has comprehensive state management that automatically:

- **Saves your work** as you go (auto-save)
- **Remembers your preferences** between sessions
- **Recovers interrupted workflows** when you refresh the page
- **Maintains analysis history** for easy access to previous results

## 🔄 How to Refresh and Remember State

### 1. **Automatic State Recovery**
When you refresh the page or reopen the app, you'll see a recovery dialog if there's previous work to restore:

- **Current Session**: Continue where you left off
- **Previous Results**: View your last analysis
- **Analysis History**: Load from any of your previous analyses

### 2. **Manual State Management**
Use the new controls in the sidebar:

- **📊 History Button**: View and load from your analysis history
- **⚙️ Settings Button**: Configure preferences and data management

### 3. **State Persistence Features**

#### **Auto-Save (Enabled by Default)**
- Your analysis progress is automatically saved
- Results are stored in your browser's local storage
- No data loss when refreshing or closing the browser

#### **Session Recovery**
- Interrupted workflows are automatically detected
- You can continue from where you left off
- Session data is cleared after 1 hour of inactivity

#### **Analysis History**
- Last 10 analyses are automatically saved
- Each entry includes file name, model used, timestamp, and results
- Easy one-click loading from history

#### **User Preferences**
- Default attribution model
- Auto-save settings
- UI preferences (theme, advanced options)
- All preferences persist between sessions

## 🛠️ Technical Implementation

### State Management Architecture

```
App.tsx
├── useAppState() - Main state management hook
├── useSessionRecovery() - Session recovery logic
├── StateRecovery.tsx - Recovery UI component
├── Settings.tsx - Preferences UI component
└── stateManager.ts - Core persistence utilities
```

### Data Storage

- **localStorage**: Persistent data (preferences, analysis history)
- **sessionStorage**: Temporary session data (current workflow)
- **Automatic cleanup**: Old session data expires after 1 hour

### State Recovery Flow

1. **App Load**: Check for recoverable state
2. **Session Check**: Look for recent session data
3. **Recovery Dialog**: Show options if data is available
4. **State Restoration**: Load selected state and continue workflow

## 🎯 Usage Examples

### Scenario 1: Page Refresh During Analysis
1. You're on step 2 (Configure Analysis) with a file selected
2. You refresh the page
3. Recovery dialog appears with "Current Session" option
4. Click "Recover Session" to continue from step 2

### Scenario 2: Viewing Previous Results
1. You completed an analysis yesterday
2. You open the app today
3. Recovery dialog shows "Previous Results" option
4. Click "View Results" to see your last analysis

### Scenario 3: Loading from History
1. You want to compare different models on the same data
2. Click the History button in the sidebar
3. Select a previous analysis from the list
4. The results load instantly with the previous model

### Scenario 4: Starting Fresh
1. You want to clear all data and start over
2. Click the History button → "Clear All Data"
3. Or use the Settings → "Reset Settings"

## ⚙️ Configuration Options

### Settings Available:
- **Default Model**: Pre-select your preferred attribution model
- **Auto-save**: Enable/disable automatic saving
- **Advanced Options**: Show/hide advanced configuration
- **Theme**: Light, Dark, or Auto (system)

### Data Management:
- **Clear History**: Remove all analysis history
- **Reset Settings**: Restore default preferences
- **Clear All Data**: Complete reset of all stored data

## 🔧 Developer Notes

### Adding New State Properties

1. **Update the interface** in `stateManager.ts`:
```typescript
export interface AppState {
  // ... existing properties
  newProperty: string;
}
```

2. **Update the default state**:
```typescript
const DEFAULT_APP_STATE: AppState = {
  // ... existing defaults
  newProperty: 'defaultValue',
};
```

3. **Add to the hook** in `useAppState.ts`:
```typescript
const setNewProperty = useCallback((value: string) => {
  setState(prev => ({ ...prev, newProperty: value }));
}, []);
```

### Custom Recovery Logic

You can extend the recovery system by modifying `useSessionRecovery.ts`:

```typescript
// Add custom recovery conditions
if (sessionState.customCondition) {
  onCustomRecovery(sessionState);
}
```

## 🚨 Troubleshooting

### State Not Persisting
- Check browser localStorage is enabled
- Verify auto-save is enabled in settings
- Clear browser cache and try again

### Recovery Dialog Not Showing
- Check if there's actually recoverable data
- Look in browser dev tools → Application → Local Storage
- Try manually triggering: `stateManager.hasRecoverableState()`

### Performance Issues
- Analysis history is limited to 10 entries
- Session data expires after 1 hour
- Large files may impact localStorage limits

## 📊 Data Structure

### Analysis History Item
```typescript
{
  id: string;           // Unique identifier
  timestamp: string;    // ISO date string
  fileName: string;     // Original file name
  model: AttributionModel; // Model used
  results: AttributionResponse; // Full results
  fileSize: number;     // File size in bytes
}
```

### User Preferences
```typescript
{
  defaultModel: AttributionModel;
  autoSave: boolean;
  showAdvancedOptions: boolean;
  theme: 'light' | 'dark' | 'auto';
}
```

This state management system ensures you never lose your work and can easily resume or review previous analyses. The implementation is robust, user-friendly, and automatically handles edge cases like browser crashes or network interruptions.
