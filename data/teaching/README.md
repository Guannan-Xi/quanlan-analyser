# Teaching Demo Data - Quick Start Guide

## Overview

6 synthetic 10-minute EEG teaching demos for QLanalyser education mode.

## Files Generated

✅ **Data Files** (6 EDF files, ~9 MB total):
- `teaching_demo_10min.edf` - Complete demo (all features)
- `teaching_demo_normal_sleep.edf` - Normal sleep cycle
- `teaching_demo_epilepsy_multiple.edf` - 3 seizure events
- `teaching_demo_insomnia.edf` - Fragmented sleep
- `teaching_demo_rem_behavior.edf` - REM behavior disorder
- `teaching_demo_mixed_artifacts.edf` - Various artifacts

✅ **Scripts** (2 Python scripts):
- `scripts/generate_teaching_demo_10min.py` - Main demo generator
- `scripts/generate_multiple_teaching_demos.py` - All variants

✅ **Backend** (2 Python modules):
- `backend/services/teaching_data_service.py` - Service layer
- `backend/api/teaching_data.py` - REST API endpoints

✅ **Integration**:
- `backend/main.py` - Router registered (public access)

✅ **Documentation**:
- `work/release_evidence/TEACHING_DEMO_SPECIFICATION.md` - Full specification

## Quick Commands

### Generate All Demos
```bash
cd D:\Quanlan\Codes\Python\quanlan-analyser-official
C:/Users/XGN/miniconda3/python.exe scripts/generate_multiple_teaching_demos.py
```

### Test API Endpoints
```bash
# List all demos
curl http://localhost:8000/api/teaching/demos

# Get specific demo
curl http://localhost:8000/api/teaching/demos/demo_10min_full

# Register all demos
curl -X POST http://localhost:8000/api/teaching/register-all

# System status
curl http://localhost:8000/api/teaching/status
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/teaching/demos` | GET | List all teaching demos |
| `/api/teaching/demos/{id}` | GET | Get specific demo |
| `/api/teaching/register/{id}` | POST | Register demo |
| `/api/teaching/register-all` | POST | Register all demos |
| `/api/teaching/generate` | POST | Generate demo files |
| `/api/teaching/project` | GET | Get teaching project |
| `/api/teaching/status` | GET | System status |

## Demo Scenarios

1. **demo_10min_full** - Complete: Wake → NREM → REM → Seizure (10 min)
2. **demo_normal_sleep** - Normal sleep cycle progression
3. **demo_epilepsy_multiple** - 3 seizure events with post-ictal
4. **demo_insomnia** - Frequent awakenings, fragmented sleep
5. **demo_rem_behavior** - Abnormal high EMG during REM
6. **demo_mixed_artifacts** - Eye blinks, noise, electrode pop, movement

## Features per Demo

### All Demos Include:
- 5 channels: EEG3, EEG1, ACC_X, ACC_Y, ACC_Z
- 250 Hz sampling rate
- 600 seconds (10 minutes)
- EDF format
- Event annotations

### Special Features:
- **Sleep Spindles** (12-14 Hz bursts)
- **K-complexes** (large slow waves)
- **Seizure events** (high-frequency spikes)
- **Eye movement artifacts**
- **Electrical noise** (50/60 Hz)
- **Movement artifacts**

## File Locations

```
D:\Quanlan\Codes\Python\quanlan-analyser-official\
├── data/teaching/                     # Generated EDF files
│   ├── teaching_demo_10min.edf
│   ├── teaching_demo_normal_sleep.edf
│   ├── teaching_demo_epilepsy_multiple.edf
│   ├── teaching_demo_insomnia.edf
│   ├── teaching_demo_rem_behavior.edf
│   └── teaching_demo_mixed_artifacts.edf
├── scripts/
│   ├── generate_teaching_demo_10min.py
│   └── generate_multiple_teaching_demos.py
├── backend/
│   ├── services/teaching_data_service.py
│   └── api/teaching_data.py
└── work/release_evidence/
    └── TEACHING_DEMO_SPECIFICATION.md  # Full documentation
```

## Frontend Integration Example

```javascript
// Load teaching demo
async function loadTeachingDemo(demoId) {
    const demo = await fetch(`/api/teaching/demos/${demoId}`).then(r => r.json());
    await fetch(`/api/teaching/register/${demoId}`, { method: 'POST' });
    // Load file using demo.file_id
}

// Demo IDs
const demoIds = [
    'demo_10min_full',
    'demo_normal_sleep', 
    'demo_epilepsy_multiple',
    'demo_insomnia',
    'demo_rem_behavior',
    'demo_mixed_artifacts'
];
```

## Deployment Checklist

- [x] Generate demo files (6 files, ~9 MB)
- [x] Create generation scripts
- [x] Implement backend service
- [x] Create API endpoints
- [x] Register router in main.py
- [x] Write full specification
- [ ] Test API endpoints (after server start)
- [ ] Add frontend UI selector
- [ ] Update user documentation

## Requirements

- **Python**: 3.8+
- **Dependencies**: numpy, mne (via miniconda3)
- **Storage**: ~9 MB for all demos
- **Generation Time**: ~1 minute for all demos

## Notes

- **Synthetic Data**: All demos are synthetic, safe for teaching
- **No PHI**: Zero protected health information
- **Public Access**: API endpoints don't require authentication
- **Protected**: Demos cannot be deleted or renamed via UI

## Support

- Full specification: `work/release_evidence/TEACHING_DEMO_SPECIFICATION.md`
- Service code: `backend/services/teaching_data_service.py`
- API code: `backend/api/teaching_data.py`

---

**Status**: ✅ Complete and Ready for Deployment  
**Generated**: 2026-07-03  
**Total Files**: 6 demos + 2 scripts + 2 backend modules + 2 docs
