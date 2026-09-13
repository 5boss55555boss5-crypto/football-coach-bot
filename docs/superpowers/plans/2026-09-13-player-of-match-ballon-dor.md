# Player of the Match and Ballon d'Or Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one optimized, position-balanced performance system that selects a Player of the Match from both teams and produces a deterministic journalist-voted Ballon d'Or ranking.

**Architecture:** Keep the established single-file application structure. Add pure rating and voting functions to `game.html`, feed them compact live/AI match aggregates, persist only season totals, and reuse the same totals for the winter preview and end-of-season ceremony.

**Tech Stack:** Vanilla HTML/CSS/JavaScript, browser `localStorage`, Node.js, Playwright with installed Microsoft Edge.

**Spec:** `docs/superpowers/specs/2026-09-13-player-of-match-ballon-dor-design.md`

## Global Constraints

- Preserve the standalone `game.html` build and add no external runtime dependencies.
- Player of the Match candidates must include every eligible player from both teams.
- Match ratings use a 3.0–10.0 range and must not award points from base overall rating.
- Ballon d'Or weighting is 45% match quality, 25% position-normalized contribution, 15% big matches/MOTM, and 15% participation-adjusted team success.
- AI matches use compact aggregates, never full pass-by-pass simulation.
- New save fields are optional; existing saves must load without changing results, squads, transfers, or calendars.
- Journalist randomness must be seeded and repeatable for a season.
- The award itself must not directly increase player overall rating or bypass seasonal progression limits.

## File Structure

- Modify `game.html`: award configuration, pure ratings, live/AI aggregation, save migration, Ballon d'Or voting, winter block, final ceremony.
- Create `scripts/regression_player_awards.js`: focused browser regression tests for ratings, MOTM, persistence, positional balance, transfers, and deterministic voting.

---

### Task 1: Pure Match Rating Engine

**Files:**
- Create: `scripts/regression_player_awards.js`
- Modify: `game.html:15008-15019`

**Interfaces:**
- Consumes: player objects with `{id,n,p,r}` and compact raw match counters.
- Produces: `emptyPlayerPerformance(player, context)`, `calculateMatchRating(perf)`, `selectPlayerOfMatch(performances)`.

- [ ] **Step 1: Write failing rating and MOTM tests**

Create a Playwright script using the repository's existing Edge launcher pattern. In `page.evaluate`, construct fixed performances and return ratings/selections:

```js
const blank = (id, n, p, extra={}) => ({
  playerId:id, name:n, position:p, clubId:extra.clubId||1,
  minutes:extra.minutes ?? 90, goals:0, assists:0, shotsOnTarget:0,
  keyPasses:0, tacklesWon:0, interceptions:0, saves:0,
  penaltiesSaved:0, goalsConceded:0, cleanSheet:false,
  yellow:0, red:false, ownGoals:0, penaltiesMissed:0,
  decisiveActions:0, result:'draw', importance:1, ...extra,
});
const quietKeeper = calculateMatchRating(blank('gk0','Тихий воротар','ВРТ',{cleanSheet:true}));
const busyKeeper = calculateMatchRating(blank('gk8','Герой воріт','ВРТ',{cleanSheet:true,saves:8}));
const defender = calculateMatchRating(blank('cb','Захисник','ЦЗ',{cleanSheet:true,tacklesWon:7,interceptions:5}));
const cameo = calculateMatchRating(blank('sub','Запасний','ЦН',{minutes:14}));
const opponentHero = calculateMatchRating(blank('opp','Форвард суперника','ЦН',{clubId:2,goals:2,decisiveActions:1,result:'win'}));
const winner = selectPlayerOfMatch([quietKeeper,busyKeeper,defender,cameo,opponentHero]);
return {quietKeeper,busyKeeper,defender,cameo,winner};
```

Assert that all ratings are within range, the busy keeper beats the quiet keeper, the defender reaches at least 7.5, the cameo is ineligible, and `winner.playerId === 'opp'`.

- [ ] **Step 2: Run the test and verify failure**

Run: `node scripts/regression_player_awards.js`

Expected: FAIL because `calculateMatchRating` is not defined.

- [ ] **Step 3: Add the centralized configuration and pure functions**

Add near the existing player-stat tracking section:

```js
const PLAYER_AWARD_CFG=Object.freeze({
  base:6,min:3,max:10,minMotmMinutes:20,
  goal:{ВРТ:2.0,DEF:1.45,MID:1.2,FWD:1.0},assist:.7,decisive:.25,
  shotOnTarget:.06,keyPass:.12,tackle:.055,interception:.07,
  save:.11,penaltySave:1.0,cleanSheet:{ВРТ:.45,DEF:.3,MID:.08,FWD:0},
  conceded:{ВРТ:.28,DEF:.12,MID:.03,FWD:0},
  yellow:.18,red:1.35,ownGoal:1.0,penaltyMiss:.75,win:.12,loss:.08,
});
function awardRole(pos){
  if(pos==='ВРТ'||pos==='GK')return 'ВРТ';
  if(isDef(pos)||['ЦЗ','ЛЗ','ПЗ'].includes(pos))return 'DEF';
  if(isMid(pos)||['ЦП','ОП','АП'].includes(pos))return 'MID';
  return 'FWD';
}
function emptyPlayerPerformance(player={},context={}){
  return {playerId:player.id||'',name:player.n||'',position:player.p||'',clubId:context.clubId,
    minutes:90,goals:0,assists:0,shotsOnTarget:0,keyPasses:0,tacklesWon:0,interceptions:0,
    saves:0,penaltiesSaved:0,goalsConceded:0,cleanSheet:false,yellow:0,red:false,
    ownGoals:0,penaltiesMissed:0,decisiveActions:0,result:'draw',importance:1,...context};
}
function calculateMatchRating(raw){
  const p={...raw},role=awardRole(p.position),c=PLAYER_AWARD_CFG;
  let value=c.base+(p.goals||0)*c.goal[role]+(p.assists||0)*c.assist+
    (p.decisiveActions||0)*c.decisive+(p.shotsOnTarget||0)*c.shotOnTarget+
    (p.keyPasses||0)*c.keyPass+(p.tacklesWon||0)*c.tackle+
    (p.interceptions||0)*c.interception+(p.saves||0)*c.save+
    (p.penaltiesSaved||0)*c.penaltySave+(p.cleanSheet?c.cleanSheet[role]:0)-
    (p.goalsConceded||0)*c.conceded[role]-(p.yellow||0)*c.yellow-
    (p.red?c.red:0)-(p.ownGoals||0)*c.ownGoal-(p.penaltiesMissed||0)*c.penaltyMiss+
    (p.result==='win'?c.win:p.result==='loss'?-c.loss:0);
  const minutes=Math.max(0,Math.min(120,Number(p.minutes)||0));
  if(minutes<45&&!(p.goals||p.assists||p.penaltiesSaved))value-=Math.min(.5,(45-minutes)/90);
  p.rating=Math.round(Math.max(c.min,Math.min(c.max,value))*10)/10;
  p.eligible=minutes>=c.minMotmMinutes||!!(p.goals||p.assists||p.penaltiesSaved||p.decisiveActions);
  p.impact=(p.decisiveActions||0)*5+(p.goals||0)*4+(p.assists||0)*2+(p.penaltiesSaved||0)*4+(p.saves||0)*.2;
  return p;
}
function selectPlayerOfMatch(rows){
  return rows.filter(p=>p?.eligible).slice().sort((a,b)=>b.rating-a.rating||b.impact-a.impact||b.minutes-a.minutes||String(a.playerId).localeCompare(String(b.playerId)))[0]||null;
}
```

- [ ] **Step 4: Run the focused test**

Run: `node scripts/regression_player_awards.js`

Expected: PASS for the pure rating assertions.

- [ ] **Step 5: Commit the pure engine**

```powershell
git add -- game.html scripts/regression_player_awards.js
git commit -m "feat: add position-balanced match ratings"
```

---

### Task 2: Feed Live Match Data and Select from Both Teams

**Files:**
- Modify: `game.html:15008-15019,15439-15449,16067-16071,18817-18910,20571-21110,35887-35893,37145-37151`
- Test: `scripts/regression_player_awards.js`

**Interfaces:**
- Consumes: `playerStats`, `LS.oppStats`, substitutions, `LS.events`, and generated team totals.
- Produces: `buildFinishedMatchPerformances(teamStats) -> Performance[]`, `LS.playerOfMatch`, `LS._teamStats`.

- [ ] **Step 1: Extend the regression with both-team integration cases**

Initialize a minimal `LS` with eleven user players, eleven opponent players, one opponent scorer and a 0:2 score. Call `buildFinishedMatchPerformances` and assert that it returns both club IDs, 22 records, valid minutes, and an opponent winner.

Also simulate an opponent substitution and assert that `LS.oppSubbedOut` retains the outgoing player's minutes and counters.

- [ ] **Step 2: Run the integration test and verify failure**

Run: `node scripts/regression_player_awards.js`

Expected: FAIL because `buildFinishedMatchPerformances` is not defined.

- [ ] **Step 3: Replace repeated stat literals with one factory**

Add and use:

```js
function emptyLivePlayerStats(){
  return {goals:0,assists:0,yellows:0,red:false,injured:false,
    shotsOnTarget:0,keyPasses:0,tacklesWon:0,interceptions:0,
    penaltiesSaved:0,penaltiesMissed:0,ownGoals:0};
}
```

Use it in `initPlayerStats`, user substitutions, opponent substitutions, ban replacements, and all fallback `_matchStats` objects. Preserve outgoing opponent players in `LS.oppSubbedOut` exactly as user players are preserved in `LS.subbedOut`.

- [ ] **Step 4: Reuse the existing movement and match-total data**

When `generateMinuteAction` reports `interception`, increment the interceptor's `interceptions`. When a successful stage-2/3 action leads into a shot or goal, increment the carrier's `keyPasses`. Record penalty misses/saves in the same counters used by the penalty engine.

Extract the technical-stat IIFE in `finishMatch` into `generateTechnicalMatchStatsData()` and call it once before selecting MOTM. Return numeric fields including `myOnTarget`, `oppOnTarget`, successful tackles, passes, possession, corners, fouls and cards; render the existing HTML from that same object so values cannot diverge.

- [ ] **Step 5: Build final performance rows**

Implement `buildFinishedMatchPerformances(teamStats)` to:

- collect starters, substituted-out players and substituted-in players for both clubs;
- compute minutes from `_enteredMin`, `_minutesPlayed`, and final match minute;
- use recorded goals, assists, discipline and movement counters;
- set goalkeeper saves to `max(0, opponent shots on target - goals conceded)`;
- distribute remaining team shots/tackles deterministically by position and player ID without using overall rating in the final score;
- mark a decisive action only when it changed the match's final winning/drawing state;
- call `calculateMatchRating` once for each row.

- [ ] **Step 6: Replace the old `motmScore` block and update the card**

Use:

```js
const performances=buildFinishedMatchPerformances(LS._teamStats);
const mom=selectPlayerOfMatch(performances);
LS.playerOfMatch=mom;
const momClub=clubById(mom?.clubId)||G.club;
const momStat=buildPlayerOfMatchSummary(mom);
```

Render the correct club logo/name, `mom.rating.toFixed(1)`, and at most three reasons. Keep the existing result card layout and avoid adding a new modal.

- [ ] **Step 7: Run and commit**

Run: `node scripts/regression_player_awards.js`

Expected: PASS, including opponent selection and substitution preservation.

```powershell
git add -- game.html scripts/regression_player_awards.js
git commit -m "feat: select player of match from both teams"
```

---

### Task 3: Compact Seasonal Award Ledger and Save Migration

**Files:**
- Modify: `game.html:6682,20600-20840,22359-22415,22480-22510,22640-22675,24124-24210`
- Test: `scripts/regression_player_awards.js`

**Interfaces:**
- Consumes: finalized `Performance[]`, selected MOTM, match competition/stage, AI scorelines.
- Produces: `G.playerAwardStats`, `recordMatchAwardStats`, `recordAIMatchAwardStats`, `awardPlayerKey`.

- [ ] **Step 1: Add failing persistence and transfer tests**

Record two performances for the same `playerId` at different clubs. Assert one ledger entry has two club IDs and combined appearances/minutes. Round-trip the ledger through the existing save sanitization path and assert ratings, MOTM count, discipline and competition participation survive.

Load a save object without `playerAwardStats` and assert migration creates an empty version-1 ledger without throwing.

- [ ] **Step 2: Run and verify failure**

Run: `node scripts/regression_player_awards.js`

Expected: FAIL because the seasonal ledger API is absent.

- [ ] **Step 3: Implement compact aggregation**

Use this shape:

```js
function ensurePlayerAwardStats(){
  const season=Number(G.seasonStartYear)||2026;
  if(!G.playerAwardStats||G.playerAwardStats.season!==season)
    G.playerAwardStats={version:1,season,players:{},revision:0};
  return G.playerAwardStats;
}
function awardPlayerKey(p){
  return String(p.playerId||p.id||('legacy:'+String(p.name||p.n||'').trim().toLowerCase()+':'+String(p.nat||'')));
}
```

Each player entry stores compact totals: identity, role, clubs map, apps, minutes, ratingSum, highRatings, goals, assists, saves, cleanSheets, keyPasses, tacklesWon, interceptions, yellows, reds, MOTM, decisiveActions, bigMatchRatingSum/count, and per-competition apps/minutes.

`recordMatchAwardStats` increments totals and the ledger revision once per completed match. It must guard with a stable match key so reopening the result screen cannot count a match twice.

- [ ] **Step 4: Add optimized AI aggregation**

For each already-simulated AI match, select the normal starting group, derive one aggregate rating from result, role and recorded goal contribution, and call `recordAIMatchAwardStats`. Do not generate movement events. Give goalkeepers saves from team shots-on-target estimates and defenders clean-sheet credit.

- [ ] **Step 5: Persist and migrate**

Increment `saveVersion` from 17 to 18. Save a sanitized compact `playerAwardStats` object; cap club history and competition keys to known values. On load, accept a valid version-1 ledger or initialize an empty ledger. In `_doNewSeason`, reset it only after the completed season's Ballon d'Or result is written.

- [ ] **Step 6: Run and commit**

Run: `node scripts/regression_player_awards.js`

Expected: PASS for transfer aggregation, duplicate protection, migration, and round-trip persistence.

```powershell
git add -- game.html scripts/regression_player_awards.js
git commit -m "feat: persist compact season award stats"
```

---

### Task 4: Position-Balanced Ballon d'Or Ranking and Journalist Vote

**Files:**
- Modify: `game.html:25510-25690,26374-26498`
- Test: `scripts/regression_player_awards.js`

**Interfaces:**
- Consumes: `G.playerAwardStats.players`, `G.scorers` fallback, trophy context.
- Produces: `buildBallonNominees(n, trophyCtx)`, `runBallonVote(nominees, season)`, `getBallonCandidates(n)` compatibility wrapper.

- [ ] **Step 1: Add failing ranking and seeded-vote tests**

Create season records for an elite striker, elite midfielder, elite defender, elite goalkeeper, low-minute UCL reserve, and a transferred player. Assert:

- all four roles can enter the top ten;
- the reserve receives less than 30% of a full starter trophy component;
- the transferred player appears once;
- requesting 30 nominees does not impose the old two-per-club cap;
- two votes with the same season return identical point totals and order;
- a nominee more than 12 composite points behind the leader cannot win from voting noise.

- [ ] **Step 2: Run and verify failure**

Run: `node scripts/regression_player_awards.js`

Expected: FAIL because the new nomination/voting functions do not exist.

- [ ] **Step 3: Replace the old formula with four named components**

Implement:

```js
function calculateBallonProfile(row,trophyCtx,rolePeers){
  const apps=Math.max(1,row.apps||0),minutes=Math.max(0,row.minutes||0);
  const avgRating=(row.ratingSum||0)/apps;
  const quality=clamp01((avgRating-6)/3)*100;
  const contribution=positionContributionPercentile(row,rolePeers);
  const big=clamp01(((row.MOTM||0)*4+(row.decisiveActions||0)*2+
    ((row.bigMatchRatingSum||0)-6*(row.bigMatchCount||0))*3)/55)*100;
  const participation=Math.min(1,minutes/Math.max(900,apps*75));
  const team=teamAchievementScore(row,trophyCtx)*participation;
  const fairPlay=Math.max(-6,-(row.reds||0)*2-(row.yellows||0)*.12);
  const total=quality*.45+contribution*.25+big*.15+team*.15+fairPlay;
  return {quality,contribution,big,team,fairPlay,total};
}
```

`positionContributionPercentile` compares role-specific per-90 output: saves/clean sheets for goalkeepers; tackles/interceptions/clean sheets plus goals for defenders; key passes/assists plus defensive work for midfielders; goals/assists/shots for forwards. Apply a minimum of 900 minutes for a normal nomination, while allowing an exceptional candidate with at least 600 minutes and a composite above the current 30th place.

- [ ] **Step 4: Implement deterministic journalist voting**

Add a small seeded PRNG local to the vote. Create 100 juror profiles whose individual/team/fair-play preferences vary by at most ±8%. Each juror evaluates only the 30 nominees, adds noise capped at ±2 composite points, ranks ten, and assigns `[15,12,10,8,7,5,4,3,2,1]`.

Return rows with `{points,firstVotes,secondVotes,rank,profile}` and break ties by first-place votes, then second-place votes, then composite score, then stable player ID.

- [ ] **Step 5: Keep compatibility and remove unfair feedback loops**

Make `getBallonCandidates(n)` return the composite preview from `buildBallonNominees`. At season end, use `runBallonVote` to select the winner. Remove the current direct `+2` overall-rating and market-value boost for winning; retain `ballonAwards`, history, achievements and visuals.

For old saves with no ledger, build fallback candidates from `G.scorers` using goals, assists and appearances, but do not restore the old base-rating multiplier or two-per-club restriction.

- [ ] **Step 6: Run and commit**

Run: `node scripts/regression_player_awards.js`

Expected: PASS for positional balance, participation, transfer merging and deterministic voting.

```powershell
git add -- game.html scripts/regression_player_awards.js
git commit -m "feat: add deterministic Ballon d'Or voting"
```

---

### Task 5: Winter Preview and Final Ceremony UI

**Files:**
- Modify: `game.html:25549-25680,25950-26040,26590-26650`
- Test: `scripts/regression_player_awards.js`

**Interfaces:**
- Consumes: nominee profiles and final vote rows.
- Produces: updated `winterBallonBlock`, compact `ballonHistory` top-ten snapshot, ceremony HTML.

- [ ] **Step 1: Add failing UI-content assertions**

Render the winter block with a goalkeeper and defender in the top three. Assert it includes average rating, role-specific output and MOTM count, and no longer displays the obsolete fixed multipliers `×5` and `×3`.

Render the completed-season block and assert it includes ranks 1–10, vote points, the winner's component breakdown, and the correct current club after a transfer.

- [ ] **Step 2: Run and verify failure**

Run: `node scripts/regression_player_awards.js`

Expected: FAIL on the new labels and top-ten vote details.

- [ ] **Step 3: Update the winter preview**

Keep the existing gold card. For every row show name, current club, position, average rating, MOTM count, and one role-specific line: goals/assists, key passes, defensive actions, or saves/clean sheets. Label it as a provisional ranking and do not simulate journalist votes in winter.

- [ ] **Step 4: Update the end-of-season ceremony and history**

Store the winner plus a compact top-ten array `{playerId,name,club,position,points,rank}` in `ballonHistory`. Render the top ten with vote points and show the winner's four rounded components. Keep the existing trophy image, achievement hooks and career history lookup.

- [ ] **Step 5: Run and commit**

Run: `node scripts/regression_player_awards.js`

Expected: PASS for winter and ceremony DOM assertions.

```powershell
git add -- game.html scripts/regression_player_awards.js
git commit -m "feat: show detailed player awards"
```

---

### Task 6: Full Regression, Performance Gate, and Deliverable

**Files:**
- Modify if required by failures: `game.html`
- Test: all `scripts/regression_*.js` plus `scripts/regression_asset_optimizer.py`
- Create deliverable: `C:\Users\k2780\Downloads\Football_Manager_v6_3_Player_Awards.html`

**Interfaces:**
- Consumes: completed implementation.
- Produces: verified standalone game file.

- [ ] **Step 1: Run syntax and focused checks**

Run:

```powershell
node scripts/regression_player_awards.js
node scripts/regression_bugfixes.js
node scripts/regression_performance_optimization.js
python scripts/regression_asset_optimizer.py
```

Expected: every command exits 0.

- [ ] **Step 2: Run the complete JavaScript regression suite**

Run each `scripts/regression_*.js` file sequentially and stop on the first non-zero exit. Expected: every script exits 0 and no browser process remains running.

- [ ] **Step 3: Add a performance assertion**

In `regression_player_awards.js`, generate 2,000 compact season entries, run `buildBallonNominees(30, ctx)` and `runBallonVote`, and assert completion under 250 ms in the browser after one warm-up run. Also assert the serialized award ledger stays below 1.5 MB for those 2,000 entries.

- [ ] **Step 4: Verify standalone integrity**

Assert `game.html` contains no required local `<script src>` or `<link href>` runtime dependency, opens through a `file:///` URL, and initializes `G` without console errors.

- [ ] **Step 5: Copy the tested artifact and verify byte identity**

Copy `game.html` to `C:\Users\k2780\Downloads\Football_Manager_v6_3_Player_Awards.html`, then compare SHA-256 hashes and file sizes. Expected: hashes and sizes match exactly.

- [ ] **Step 6: Commit final test adjustments**

```powershell
git add -- game.html scripts/regression_player_awards.js
git commit -m "test: verify optimized player awards"
```
