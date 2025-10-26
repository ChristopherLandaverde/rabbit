# 🎯 State Management Demo

## How to Test State Persistence & Recovery

### 1. **Test Auto-Save During Analysis**
1. Start the frontend: `npm run dev`
2. Upload a file and configure analysis
3. **Don't run the analysis yet** - just refresh the page
4. You should see a "Recovery Dialog" with "Current Session" option
5. Click "Recover Session" - you'll be back at step 2 with your file selected

### 2. **Test Results Persistence**
1. Complete a full analysis (upload → configure → analyze)
2. Refresh the page
3. Recovery dialog shows "Previous Results" option
4. Click "View Results" - you'll see your analysis results

### 3. **Test Analysis History**
1. Complete multiple analyses with different models
2. Click the **History button** (📊) in the sidebar
3. You'll see a list of your previous analyses
4. Click any item to load those results instantly

### 4. **Test Settings Persistence**
1. Click the **Settings button** (⚙️) in the sidebar
2. Change your default model to "Time Decay"
3. Enable/disable auto-save
4. Close and reopen the app
5. Your settings should be remembered

### 5. **Test Session Recovery**
1. Start an analysis (upload a file)
2. Close the browser tab completely
3. Reopen the app
4. You should see the recovery dialog
5. Choose to continue your session

### 6. **Test Data Clearing**
1. Go to Settings → "Clear All Data"
2. Or use History → "Clear All Data"
3. Refresh the page
4. No recovery dialog should appear (fresh start)

## 🔍 What to Look For

### ✅ **Working Correctly:**
- Recovery dialog appears when there's previous work
- Settings persist between sessions
- Analysis history saves automatically
- Session state recovers interrupted workflows
- Data clears when requested

### ❌ **Potential Issues:**
- No recovery dialog = localStorage might be disabled
- Settings not saving = check browser permissions
- History not showing = auto-save might be disabled
- Session not recovering = check sessionStorage support

## 🛠️ Developer Testing

### Check Browser Storage:
1. Open DevTools → Application tab
2. Look at Local Storage → `http://localhost:5173`
3. You should see keys like:
   - `rabbit_app_state`
   - `rabbit_user_preferences`
   - `rabbit_analysis_history`

### Check Session Storage:
1. Look at Session Storage → `http://localhost:5173`
2. You should see `rabbit_session_state` when workflow is active

### Console Logging:
- State changes are logged to console
- Recovery actions are logged
- Error messages appear for storage issues

## 🎨 UI Features to Test

### Sidebar Controls:
- **📊 History Button**: Opens recovery/history dialog
- **⚙️ Settings Button**: Opens preferences dialog

### Recovery Dialog:
- Shows different recovery options based on available data
- Clean, intuitive interface for choosing what to restore
- Clear data option for fresh start

### Settings Dialog:
- All preferences in one place
- Real-time preview of changes
- Reset to defaults option

## 🚀 Advanced Testing

### Test Edge Cases:
1. **Large Files**: Upload very large CSV files
2. **Multiple Tabs**: Open app in multiple browser tabs
3. **Network Issues**: Disconnect internet during analysis
4. **Browser Crash**: Force close browser during workflow
5. **Storage Limits**: Fill up localStorage to test limits

### Test Performance:
1. **Many Analyses**: Create 10+ analyses to test history limits
2. **Large Results**: Use files with many touchpoints
3. **Rapid Changes**: Quickly switch between different analyses

This comprehensive state management system ensures your MVP never loses user work and provides a smooth, professional experience even when things go wrong!
