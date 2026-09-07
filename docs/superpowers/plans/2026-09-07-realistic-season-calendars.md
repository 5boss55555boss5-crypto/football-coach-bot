# Realistic Season Calendars Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every playable league and both UEFA competitions a realistic 2026/27 date pattern, visible pauses, safe collision handling, and backward-compatible saved-game migration.

**Architecture:** Keep the game as one portable `game.html`, but split calendar responsibilities into profile data, pure date helpers, schedule composition, and save migration. Round-robin generation owns pairings only; a calendar layer assigns `calendarDate`, inserts pauses, merges cups and Europe chronologically, and preserves played save history.

**Tech Stack:** Standalone HTML/JavaScript, browser `Date`, Node.js `assert`, Playwright with Microsoft Edge.

**Spec:** `docs/superpowers/specs/2026-09-07-realistic-season-calendars-design.md`

## Global Constraints

- Keep `game.html` self-contained; add no runtime package or network dependency.
- Preserve every league’s club count, round count, generated pairings, domestic-cup format, UEFA participant count, and UEFA play-off match count.
- Do not add UEFA knockout play-off rounds; the existing play-off begins at the round of 16.
- Use 2026/27 as the authoritative template and shift future templates to the nearest normal match day.
- Store machine dates as `calendarDate: "YYYY-MM-DD"`; keep `date` as Ukrainian display text.
- International pauses are visible, consume one Continue action, recover energy, and never open the transfer market.
- Never alter played results or the played prefix of an old save.
- Stage only task-specific hunks from the already-dirty `game.html`; never commit unrelated working-tree changes.

---

### Task 1: Calendar profile data and pure date helpers

**Files:**
- Create: `scripts/regression_calendar_profiles.js`
- Modify: `game.html:7880-8004`

**Interfaces:**
- Consumes: `G.seasonStartYear`, league ids from `LEAGUES`.
- Produces: `CALENDAR_VERSION`, `INTERNATIONAL_BREAKS`, `SEASON_CALENDAR_PROFILES`, `UEFA_CALENDAR_PROFILES`, `calendarIsoDate(monthDay, seasonStartYear)`, `calendarDisplayDate(iso)`, and `getCalendarProfile(leagueId)`.

- [ ] **Step 1: Write the failing profile test**

Create a Playwright test that loads the real game and evaluates the desired globals:

```js
const assert = require('assert');
const path = require('path');
const { pathToFileURL } = require('url');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    executablePath:'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    headless:true,
  });
  const page = await browser.newPage();
  await page.goto(pathToFileURL(path.resolve(__dirname,'..','game.html')).href);
  const actual = await page.evaluate(() => ({
    version:CALENDAR_VERSION,
    leagues:Object.fromEntries(Object.entries(SEASON_CALENDAR_PROFILES).map(([id,p]) => [id, {
      start:calendarIsoDate(p.start,2026),end:calendarIsoDate(p.end,2026),winter:p.winter,
    }])),
    ucl:UEFA_CALENDAR_PROFILES.ucl,
    uel:UEFA_CALENDAR_PROFILES.uel,
  }));
  assert.strictEqual(actual.version,2);
  assert.deepStrictEqual(Object.keys(actual.leagues).sort(),['bundesliga','epl','laliga','ligue1','other','seriea','upl']);
  assert.deepStrictEqual([actual.leagues.epl.start,actual.leagues.epl.end],['2026-08-21','2027-05-30']);
  assert.deepStrictEqual([actual.leagues.upl.start,actual.leagues.upl.end],['2026-08-01','2027-06-04']);
  assert.deepStrictEqual(actual.ucl.league,['09-09','10-14','10-21','11-04','11-25','12-09','01-20','01-27']);
  assert.deepStrictEqual(actual.uel.league,['09-17','10-15','10-22','11-05','11-26','12-10','01-21','01-28']);
  await browser.close();
  console.log(JSON.stringify({ok:true,profiles:7}));
})().catch(error=>{console.error(error.stack||error);process.exit(1);});
```

- [ ] **Step 2: Run the test and verify RED**

```powershell
$env:NODE_PATH='C:\Users\k2780\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
& 'C:\Users\k2780\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' '.\scripts\regression_calendar_profiles.js'
```

Expected: `ReferenceError: CALENDAR_VERSION is not defined`.

- [ ] **Step 3: Add immutable calendar profiles**

Insert near `buildRoundRobin()`:

```js
const CALENDAR_VERSION=2;
const INTERNATIONAL_BREAKS=[
  {start:'09-21',end:'10-06',label:'🌍 Міжнародна пауза'},
  {start:'11-09',end:'11-17',label:'🌍 Міжнародна пауза'},
  {start:'03-22',end:'03-30',label:'🌍 Міжнародна пауза'},
];
const SEASON_CALENDAR_PROFILES=Object.freeze({
  epl:{start:'08-21',end:'05-30',rounds:38,weekday:6,winter:null,midweekRounds:5},
  laliga:{start:'08-15',end:'05-30',rounds:38,weekday:0,midweekRounds:4,winter:{afterRound:17,start:'12-21',end:'01-02',resume:'01-03'}},
  seriea:{start:'08-23',end:'05-30',rounds:38,weekday:0,midweekRounds:2,winter:{afterRound:16,start:'12-21',end:'01-02',resume:'01-03',kind:'calendar'}},
  bundesliga:{start:'08-28',end:'05-22',rounds:34,weekday:6,midweekRounds:1,winter:{afterRound:14,start:'12-21',end:'01-07',resume:'01-08'}},
  upl:{start:'08-01',end:'06-04',rounds:30,weekday:6,winter:{afterRound:16,start:'12-13',end:'02-26',resume:'02-27'}},
  ligue1:{start:'08-21',end:'05-29',rounds:34,weekday:6,winter:{afterRound:14,start:'12-14',end:'01-01',resume:'01-02'}},
  other:{start:'08-22',end:'05-29',rounds:30,weekday:6,winter:{afterRound:15,start:'12-20',end:'01-08',resume:'01-09'}},
});
const UEFA_CALENDAR_PROFILES=Object.freeze({
  ucl:{draw:'08-27',league:['09-09','10-14','10-21','11-04','11-25','12-09','01-20','01-27'],r16:['03-10','03-17'],qf:['04-07','04-14'],sf:['04-28','05-05'],final:'06-05'},
  uel:{draw:'08-28',league:['09-17','10-15','10-22','11-05','11-26','12-10','01-21','01-28'],r16:['03-11','03-18'],qf:['04-08','04-15'],sf:['04-29','05-06'],final:'05-26'},
});
function calendarIsoDate(monthDay,seasonStartYear){
  const month=Number(monthDay.slice(0,2));
  return String(month>=7?seasonStartYear:seasonStartYear+1)+'-'+monthDay;
}
function calendarDisplayDate(iso){
  const [year,month,day]=iso.split('-').map(Number);
  return new Date(year,month-1,day).toLocaleDateString('uk-UA',{day:'numeric',month:'short'});
}
function getCalendarProfile(leagueId){
  return SEASON_CALENDAR_PROFILES[leagueId]||SEASON_CALENDAR_PROFILES.other;
}
```

- [ ] **Step 4: Run the new test and all domestic-league tests**

Run `regression_calendar_profiles.js`, `regression_epl_2026.js`, `regression_laliga_2026.js`, `regression_seriea_2026.js`, `regression_bundesliga_2026.js`, and `regression_ligue1.js`.

Expected: every test exits 0; schedule behavior remains unchanged until Task 2.

- [ ] **Step 5: Commit only the profile hunk and test**

```powershell
git add -- scripts/regression_calendar_profiles.js
git add -p -- game.html
git diff --cached --check
git commit -m "feat: define season calendar profiles"
```

Accept only the profile/helper hunk from `game.html`.

---

### Task 2: Apply league dates and render visible pauses

**Files:**
- Create: `scripts/regression_league_calendar_dates.js`
- Modify: `game.html:7880-8033`
- Modify: `game.html:20303-20340`
- Modify: `game.html:22520-22535`
- Modify: `game.html:23459-23530`
- Modify: `game.html:25874-25886`
- Modify: `game.html:25990-26150`

**Interfaces:**
- Consumes: Task 1 profiles/helpers and round arrays from `buildRoundRobin()`.
- Produces: `buildLeagueRoundDates(leagueId, seasonStartYear, roundCount)`, `applyLeagueCalendarProfile(schedule, leagueId, seasonStartYear)`, `isSchedulePause(round)`, and `continuePastCalendarPause()`.

- [ ] **Step 1: Write the failing league-date test**

Use production functions for every league:

```js
const audit=await page.evaluate(() => Object.fromEntries(LEAGUES.map(league => {
  const ids=CLUBS.filter(club=>league.filter(club)).map(club=>club.id);
  const schedule=applyLeagueCalendarProfile(buildRoundRobin(ids),league.id,2026);
  const rounds=schedule.filter(item=>typeof item.round==='number');
  const pauses=schedule.filter(item=>isSchedulePause(item));
  return [league.id,{
    rounds:rounds.length,
    first:rounds[0].calendarDate,
    last:rounds.at(-1).calendarDate,
    winter:pauses.filter(item=>item.breakKind==='winter').map(item=>item.afterRound),
    international:pauses.filter(item=>item.breakKind==='international').length,
    chronological:schedule.every((item,index,array)=>!index||array[index-1].calendarDate<=item.calendarDate),
  }];
})));
assert.deepStrictEqual(audit.epl,{rounds:38,first:'2026-08-21',last:'2027-05-30',winter:[],international:3,chronological:true});
assert.deepStrictEqual(audit.bundesliga.winter,[14]);
assert.deepStrictEqual(audit.upl.winter,[16]);
assert.deepStrictEqual(audit.ligue1.winter,[14]);
```

- [ ] **Step 2: Run the test and verify RED**

Expected: `ReferenceError: applyLeagueCalendarProfile is not defined`.

- [ ] **Step 3: Separate pair generation from calendar generation**

Remove the hard-coded `ЗИМА` row from `buildRoundRobin()`. Implement:

```js
function isDateInside(iso,start,end){return iso>=start&&iso<=end;}
function buildLeagueRoundDates(leagueId,seasonStartYear,roundCount){
  const profile=getCalendarProfile(leagueId);
  const start=calendarIsoDate(profile.start,seasonStartYear);
  const end=calendarIsoDate(profile.end,seasonStartYear);
  const blocked=INTERNATIONAL_BREAKS.map(item=>({
    start:calendarIsoDate(item.start,seasonStartYear),
    end:calendarIsoDate(item.end,seasonStartYear)
  }));
  if(profile.winter)blocked.push({
    start:calendarIsoDate(profile.winter.start,seasonStartYear),
    end:calendarIsoDate(profile.winter.end,seasonStartYear)
  });
  const candidates=[];
  for(let date=new Date(start+'T12:00:00');date<=new Date(end+'T12:00:00');date.setDate(date.getDate()+1)){
    const iso=date.toISOString().slice(0,10);
    if(date.getDay()===profile.weekday&&!blocked.some(range=>isDateInside(iso,range.start,range.end)))candidates.push(iso);
  }
  return selectCalendarDates(candidates,roundCount,start,end,profile.midweekRounds||0);
}
```

Use the published full arrays for UPL and Ligue 1:

```js
const EXACT_LEAGUE_ROUND_DATES={
  upl:['08-01','08-08','08-15','08-29','09-05','09-12','09-19','10-10','10-17','10-24','10-31','11-07','11-21','11-28','12-05','12-12','02-27','03-06','03-13','03-20','04-03','04-10','04-17','04-24','05-01','05-08','05-15','05-22','05-29','06-04'],
  ligue1:['08-21','08-29','09-05','09-12','09-19','10-10','10-17','10-24','10-31','11-07','11-21','11-28','12-05','12-12','01-02','01-16','01-23','01-30','02-06','02-13','02-20','02-27','03-06','03-13','03-20','04-03','04-10','04-17','04-24','05-01','05-08','05-16','05-22','05-29'],
};
function selectEvenly(values,count){
  if(count<=0)return [];
  if(count===1)return [values[0]];
  return Array.from({length:count},(_,index)=>values[Math.round(index*(values.length-1)/(count-1))]);
}
function selectCalendarDates(weekends,midweeks,roundCount,start,end,midweekCount){
  const innerWeekendCount=Math.max(0,roundCount-midweekCount-2);
  const weekendPool=weekends.filter(date=>date!==start&&date!==end);
  const selected=[start,...selectEvenly(weekendPool,innerWeekendCount),...selectEvenly(midweeks,midweekCount),end];
  const unique=[...new Set(selected)].sort();
  if(unique.length!==roundCount)throw new Error('Calendar profile cannot provide '+roundCount+' unique dates');
  return unique;
}
```

Generate `midweeks` from Wednesdays inside the season that are outside blocked ranges and at least three days from either anchor. For 2026/27 return `EXACT_LEAGUE_ROUND_DATES[leagueId].map(monthDay=>calendarIsoDate(monthDay,seasonStartYear))` when an exact array exists. For later seasons convert every template date and move non-anchor dates to the nearest `profile.weekday` within three days; this is the concrete future-season shifting rule.

- [ ] **Step 4: Assign dates and insert typed pause events**

`applyLeagueCalendarProfile()` assigns league round dates and inserts:

```js
{
  round:'PAUSE',matches:[],calendarDate:start,date:displayRange,
  phase:kind==='winter'?'break':'international_break',
  breakKind:kind,label:kind==='winter'?'❄️ Зимова пауза':'🌍 Міжнародна пауза',afterRound
}
```

Replace direct `buildRoundRobin()` schedule assignments in `confirmClub()`, `_doNewSeason()`, and `switchManagerClub()` with:

```js
G.schedule=applyLeagueCalendarProfile(
  fixUserHomeAwayPattern(buildRoundRobin(leagueClubIds),G.club.id),
  G.leagueId,
  G.seasonStartYear||2026
);
```

- [ ] **Step 5: Render and advance non-winter pauses**

Add `isSchedulePause()`; keep `isWinterBreak()` true only for `breakKind==='winter'`. Render international/calendar pause cards before the winter branch in `renderNextMatch()`, in `renderSchedule()`, and in the month grid. Their button calls:

```js
function continuePastCalendarPause(){
  G.players.forEach(player=>{
    player.energy=Math.min(100,(player.energy||100)+8);
    player.fatigue=Math.max(0,(player.fatigue||0)-2);
  });
  advanceRound('calendar-pause',{processUCL:false,skipAcademy:true,skipContractWarning:true,save:true});
  renderNextMatch();renderSchedule();renderTable();
}
```

Update every round/progress filter to ignore `isSchedulePause(rd)`.

- [ ] **Step 6: Run Task 2 and domestic-league regressions**

Expected: APL has no winter card; UPL resumes on 27 February; every league retains its existing number of rounds and matches; there are no page errors.

- [ ] **Step 7: Commit only Task 2 hunks and test**

```powershell
git add -- scripts/regression_league_calendar_dates.js
git add -p -- game.html
git diff --cached --check
git commit -m "feat: schedule league seasons on realistic dates"
```

---

### Task 3: UEFA dates, chronological merge, and cup collision handling

**Files:**
- Create: `scripts/regression_european_calendar_dates.js`
- Modify: `game.html:7919-8004`
- Modify: `game.html:28493-29510`

**Interfaces:**
- Consumes: Task 1/2 dates, `initCupSchedule()`, `initUCLSchedule()`, `initUELSchedule()`, `injectUCLPlayoff()`, and `injectUELPlayoff()`.
- Produces: `getEuropeanCalendarDate(competition, stage, index, seasonStartYear)`, `mergeScheduleChronologically(schedule)`, and `findNearestFreeCupDate(preferredIso, occupiedIsoDates, minGapDays)`.

- [ ] **Step 1: Write the failing UEFA-date test**

```js
assert.strictEqual(getEuropeanCalendarDate('ucl','draw',0,2026),'2026-08-27');
assert.strictEqual(getEuropeanCalendarDate('ucl','league',7,2026),'2027-01-27');
assert.deepStrictEqual([0,1].map(i=>getEuropeanCalendarDate('ucl','r16',i,2026)),['2027-03-10','2027-03-17']);
assert.strictEqual(getEuropeanCalendarDate('ucl','final',0,2026),'2027-06-05');
assert.deepStrictEqual([0,1].map(i=>getEuropeanCalendarDate('uel','sf',i,2026)),['2027-04-29','2027-05-06']);
assert.strictEqual(getEuropeanCalendarDate('uel','final',0,2026),'2027-05-26');
```

The integration part initializes a real European schedule and asserts eight league events, unchanged play-off leg counts, ascending `calendarDate`, and no two user matches on one date.

- [ ] **Step 2: Run it and verify RED**

Expected: `ReferenceError: getEuropeanCalendarDate is not defined`.

- [ ] **Step 3: Map existing UEFA events to official dates**

```js
function getEuropeanCalendarDate(comp,stage,index,seasonStartYear){
  const profile=UEFA_CALENDAR_PROFILES[comp];
  const monthDay=stage==='draw'||stage==='final'?profile[stage]:profile[stage][index];
  return calendarIsoDate(monthDay,seasonStartYear);
}
```

Assign `calendarDate` to draw and group rows. Replace current UCL/UEL `fixedDates` for `r16`, `qf`, `sf`, and `final`. Do not create the official knockout play-off stage.

- [ ] **Step 4: Replace sequential compression with chronological merge**

Refactor `finalizeScheduleDates()` so it never overwrites `calendarDate`. Convert legacy `fixedDate` once, assign cup dates only when absent, sort, then populate `date`, `_y`, `_m`, and `_d`.

```js
function mergeScheduleChronologically(schedule){
  return schedule.map((item,index)=>({...item,_calendarOrder:index}))
    .sort((a,b)=>String(a.calendarDate).localeCompare(String(b.calendarDate))||a._calendarOrder-b._calendarOrder)
    .map(item=>{delete item._calendarOrder;return item;});
}
```

- [ ] **Step 5: Put domestic cup rounds into free slots**

Keep current stages/matches. Convert `getCupDate(stage)` into preferred ISO dates. `findNearestFreeCupDate()` moves only conflicts, keeps at least three days from adjacent user matches, and stays in the stage’s month window.

- [ ] **Step 6: Run UEFA, cup, and bugfix regressions**

Run the new test plus `regression_french_europe.js`, `regression_coupe_france.js`, all domestic-league cup tests, and `regression_bugfixes.js`.

Expected: exact UEFA dates, unchanged play-off structure, no duplicate user date, all exit 0.

- [ ] **Step 7: Commit Task 3 hunks and test**

```powershell
git add -- scripts/regression_european_calendar_dates.js
git add -p -- game.html
git diff --cached --check
git commit -m "feat: align European competitions with UEFA calendar"
```

---

### Task 4: Backward-compatible calendar migration

**Files:**
- Create: `scripts/regression_calendar_save_migration.js`
- Modify: `game.html:21028-21380`
- Modify: `game.html:36540-36560`

**Interfaces:**
- Consumes: sanitized saved schedule, `currentRound`, `leagueId`, `seasonStartYear`, existing `loadGame()`, and Tasks 1–3 helpers.
- Produces: persisted `calendarVersion`, `migrateSavedCalendar(schedule, currentRound, leagueId, seasonStartYear)`, and idempotent load behavior.

- [ ] **Step 1: Write the failing migration test**

Create a real save, mark two prefix matches played, remove `calendarVersion` and every `calendarDate`, load it, then assert:

```js
assert.strictEqual(result.loaded,true);
assert.strictEqual(result.calendarVersion,2);
assert.deepStrictEqual(result.playedPrefixAfter,result.playedPrefixBefore);
assert(result.future.every(event=>/^\d{4}-\d{2}-\d{2}$/.test(event.calendarDate)));
assert(result.future.every((event,index,array)=>!index||array[index-1].calendarDate<=event.calendarDate));
assert.strictEqual(result.currentRound,result.originalCurrentRound);
```

Load the migrated serialized save a second time and assert its schedule is byte-for-byte unchanged.

- [ ] **Step 2: Run it and verify RED**

Expected: no `calendarVersion: 2`, or future events still lack `calendarDate`.

- [ ] **Step 3: Persist version 2**

Add `calendarVersion:CALENDAR_VERSION` next to `seasonStartYear` and `schedule` in the save object written by `writeSaveGame()`/`flushSaveGame()`.

- [ ] **Step 4: Implement suffix-only migration**

```js
function migrateSavedCalendar(schedule,currentRound,leagueId,seasonStartYear){
  const prefix=schedule.slice(0,currentRound);
  const future=schedule.slice(currentRound);
  const migrated=redateFutureSchedule(future,leagueId,seasonStartYear);
  if(!migrated)return schedule;
  return prefix.concat(mergeScheduleChronologically(migrated));
}
```

Preserve every serialized prefix object and its order. Match future league rounds by numeric `round`, cups by `cupStage`, UEFA groups by occurrence index, and UEFA play-offs by `ucl_po`/`uel_po` plus leg. If any required match is ambiguous, return the original schedule. Run migration only after league, cup, and UEFA state are restored.

- [ ] **Step 5: Make migration idempotent and compatible with localization**

Skip migration when `d.calendarVersion===CALENDAR_VERSION`. Keep `loadGameWithUkrainianNames`; it calls the calendar-aware loader once and never transforms schedule order.

- [ ] **Step 6: Run migration, localization, and bugfix tests**

Expected: first load migrates future events only, second load is unchanged, `regression_player_name_localization.js` passes, and `regression_bugfixes.js` passes.

- [ ] **Step 7: Commit migration hunks and test**

```powershell
git add -- scripts/regression_calendar_save_migration.js
git add -p -- game.html
git diff --cached --check
git commit -m "feat: migrate saved careers to calendar v2"
```

---

### Task 5: End-to-end verification and distributable artifact

**Files:**
- Modify only if a failing regression proves necessary: `game.html`
- Verify: every `scripts/regression_*.js`
- Update: `C:\Users\k2780\Downloads\Football_Manager_v5_3_Bundesliga.html`

**Interfaces:**
- Consumes: all calendar APIs and pre-existing game systems.
- Produces: verified standalone game and byte-identical Downloads copy.

- [ ] **Step 1: Run every regression test**

Enumerate `scripts/regression_*.js` and run each with the bundled Node runtime and `NODE_PATH`. Record every exit code; no test may be omitted.

- [ ] **Step 2: Run an end-to-end browser audit for all seven leagues**

For each league, start a fresh career, inspect the full schedule, and advance every pause type. Require:

```js
{
  pageErrors:[],
  chronological:true,
  duplicateUserMatchDates:[],
  leagueRoundCount:expectedRoundCount,
  calendarVersion:2,
  finalDate:expectedFinalDate
}
```

- [ ] **Step 3: Verify future-season shifting**

Generate 2027/28 schedules for every profile. Assert unchanged round counts, no duplicate dates, dates inside the shifted season, and normal profile weekdays except declared midweek rounds.

- [ ] **Step 4: Copy and hash the verified game**

```powershell
Copy-Item -LiteralPath 'C:\Users\k2780\ai\football_coach_bot\game.html' -Destination 'C:\Users\k2780\Downloads\Football_Manager_v5_3_Bundesliga.html' -Force
Get-FileHash -Algorithm SHA256 -LiteralPath 'C:\Users\k2780\ai\football_coach_bot\game.html','C:\Users\k2780\Downloads\Football_Manager_v5_3_Bundesliga.html'
```

Expected: hashes are identical.

- [ ] **Step 5: Commit a verification fix only when one was required**

If verification required a calendar fix, stage only that `game.html` hunk with `git add -p -- game.html`, add its direct regression file, run `git diff --cached --check`, and commit with `git commit -m "fix: stabilize realistic season calendars"`. If verification changed no code, create no empty commit.
