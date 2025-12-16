# UX Improvements Implementation Plan

## Status: IN PROGRESS

### Completed ✅
1. **Unified Upload Endpoint** - `/api/analyze/evtc` now handles both single and multiple files
2. **Draws Counter** - Added draws tracking to evening analysis summary

### In Progress ⏳

#### 3. Group Colors in Squad Display
- Add different background colors per group (1-5) in "Ton escouade" section
- Colors: Group 1 (blue), Group 2 (green), Group 3 (yellow), Group 4 (orange), Group 5 (purple)

#### 4. Simplified Evening Summary
Keep only:
- Number of fights
- Victories/Defeats/Draws
- Time spent in fights
- Number of players
- Squad composition
- Top 10 damage dealers
- Fight details

Remove:
- Number of specializations played

#### 5. Reorganize Stats Tabs
- **Combat** tab first (currently 2nd)
- Move **Down Contrib** from Combat to Dégâts tab

#### 6. Add Distance to Tag
- Add "Distance au tag" metric in Combat tab
- Show average distance to Commander tag
- Note: Requires position data from EVTC (may not always be available)

#### 7. Simplify Boons Display
- Show only main boons by default: Aegis, Protection, Quickness, Resistance, Stability
- Hide secondary boons: Might, Fury, Regeneration, Resolution, Swiftness, Alacrity
- Add toggle button to show/hide secondary boons

#### 8. Remove Stab Percentage
- Change Stability display to remove the percentage

#### 9. Add Break Stuns in Support
- Add counter for break stuns used on group by player

#### 10. Add CC Received in Défensif
- Add counter for Crowd Control effects received

## Technical Notes

### Files to Modify
- `main.py` - Backend logic ✅ (partially done)
- `templates/partials/dps_report_result.html` - Single fight display
- `templates/partials/evening_result_v2.html` - Evening summary
- `parser.py` - Add position tracking for distance to tag (if possible)
- `counter_ai.py` - Update data structures if needed

### Data Requirements
- Distance to tag: Requires position data from EVTC logs
- Break stuns: Requires parsing specific skill IDs
- CC received: Requires parsing CC effect events

## Next Steps
1. Add group colors CSS and HTML modifications
2. Simplify evening summary template
3. Reorganize stats tabs order
4. Implement boons toggle
5. Add new metrics (break stuns, CC received)
6. Test locally
7. Deploy to server
