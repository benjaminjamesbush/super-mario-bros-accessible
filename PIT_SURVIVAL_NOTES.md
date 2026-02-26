# Pit Survival Patch - Current Issue Notes

## Goal
When Mario falls into a pit, instead of dying, he should bounce out with enough upward velocity to clear the pit walls and continue playing. No extra buttons, no teleportation, no filling pits with floor.

## Current Approach (Patch 1)
Replaced the death check + death routine (65 bytes at file $3189-$31C9) with:

1. **Early Y-floor catch**: Every frame, check if Mario is falling (State == 2) with Y >= $C0 (ground level threshold) in the normal play area (HighPos == 1)
2. **Boost**: Set Player_Y_Speed to $F4 (springboard velocity), zero MoveForce, set Player_State to 1 (jumping) to prevent re-triggering
3. **Deep fall backup**: If HighPos >= 2 (full screen below), reset to play area and apply same boost

The state=1 (jumping) trick prevents the boost from firing every frame — it can only re-trigger after the game naturally transitions back to state 2 (falling) at the arc's peak.

## Current Bug: Perpetual Upward Zoom in 1-3
In World 1-3 (treetop/bridge level), Mario zooms upward perpetually — never falls back down. Works better in 1-1 (ground level) but inconsistently.

### Likely Cause
Setting Player_State to 1 (jumping) may interact badly with SMB1's jump physics:

- **State 1 (jumping)**: The game applies LOWER gravity when A button is held (allowing higher jumps). If the player happens to hold A, or if the game's input handling treats the state change as a "new jump," gravity may be reduced so much that Mario barely decelerates.
- **In treetop levels (1-3)**: The level geometry and/or area type flags might change physics parameters. Underground (1-2) and bridge (1-3) levels may use different vertical physics tables.
- The game's jump code may also reset or modify velocity when entering state 1, causing unpredictable interactions with our forced velocity.

### What Hasn't Worked
| Approach | Result |
|----------|--------|
| Fill pits with floor (patches 1-4) | Creates depressions/bathtubs that trap Mario |
| Teleport to Y=$20 (top of screen) | Spawns inside bricks, gets stuck above ceiling |
| Teleport to Y=$D0 + high velocity | Clips through bricks (drifted out of pit's air column) |
| Early catch + boost (state unchanged) | Boost fires every frame → zooming through screen |
| Early catch + boost + state=1 (jumping) | Inconsistent: works in 1-1, perpetual zoom in 1-3 |
| Various velocities ($F4 to $FB) | Too strong clips/zooms, too weak can't clear walls |

### Velocity Tests
- $FB (-5): WAY too weak, can't clear pit walls
- $F8 (-8): Still too weak
- $F6 (-10): Still too weak
- $F4 (-12): Correct height in 1-1, but causes zoom in 1-3

## Key Constraints
- **No extra buttons** — cognitively impaired players can't learn new controls
- **No teleportation** — spawning at fixed Y positions puts Mario inside level geometry
- **No pit filling** — creates depression traps with walls too high to escape
- **No movement buffs (higher jump / air jump)** — causes sequence breaks (e.g., jumping over flagpole, getting stuck in unintended areas)
- **No checkpoint restart** — checkpoints too far apart (level start), player replays too much, leads to frustration
- **Single bounce must clear walls** — multiple bounces don't help because pit walls block horizontal movement
- **Must work across all level types** — outdoor (1-1), underground (1-2), treetop/bridge (1-3), castle (1-4), water, etc.

## Ideas to Investigate Next

### 1. Don't use State=1, use a RAM flag instead
Instead of setting Player_State to 1 (which interferes with jump physics), find an unused RAM byte to use as a "boost applied" flag. Set it when boost fires, clear it when Mario lands (state becomes 0). Only allow boost when flag is clear. This decouples the boost from the jump physics system entirely.

Challenges: need to find a consistently unused RAM byte, and need to clear the flag when Mario lands (which happens in code we don't control — would need to hook another routine or check state==0 in our per-frame code).

### 2. Use a frame counter instead of state
After boost fires, set a countdown (e.g., 30 frames). During the countdown, don't allow re-triggering. This gives Mario time to arc up and come back down without repeated boosting. Could store the counter in an unused RAM byte.

### 3. Check velocity direction
Only trigger boost when Player_Y_Speed is positive (moving downward). This prevents re-triggering on the way down from a bounce, because... wait, on the way down the speed IS positive. This doesn't help.

### 4. Hybrid: fill pits + moderate boost
Go back to filling pits (patches 1-4 with $18 floor) to prevent the deepest falls, and use the early catch as a backup for shallow depressions only. With shallower depressions, a weaker velocity works and the issues are less severe.

### 5. Research SMB1's jump state machine more deeply
Understand exactly what happens when Player_State is set to 1 externally. Does the game's JumpEngine or PlayerPhysicsSub do something unexpected? Does it read controller state and modify velocity? Does gravity differ by area type? The disassembly at https://gist.github.com/1wErt3r/4048722 has the answers.

## Technical Reference
- File offset = CPU_addr - $8000 + $10
- Patch area: file $3189-$31C9 (65 bytes), CPU $B179-$B1C9
- ExitCtrl: CPU $B1BA (file $31CA), original RTS untouched
- Player_Y_HighPos: $B5 (0=above screen, 1=play area, 2+=below screen)
- Player_Y_Position: $CE (0=top, $FF=bottom within HighPos page)
- Player_Y_Speed: $9F (signed: negative=up, positive=down)
- Player_Y_MoveForce: $0433 (sub-pixel accumulator)
- Player_State: $1D (0=ground, 1=jumping, 2=falling, 3=climbing)
- Springboard velocity: $F4 (-12)
- Normal jump velocity: ~$FB (-5)
- Current Y threshold: $C0 (roughly ground level)
