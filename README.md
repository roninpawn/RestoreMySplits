# Restore My Splits!
A python script to restore an overwritten speedrun from your Livesplit LSS splits file.

### Here's my story:
I was speedrunning Clustertruck one day, grinding for that sweet sub-15m time, and I brought in a new PB! A 15m 01s time. No kidding. One second off the sub-15. Ain't that just the way?

Anyway, I bring OBS to the top to stop my recording and I find out that my Livesplit overlay wasn't showing during the run. Now, that's not a problem for timing or verification here. I _can_ submit to our leaderboards without the timer.

But it still sucks! I was running against an old PB that absolutely destroyed the early game, and I wanted to be able to see how much give and take there was throughout the run. It helps me feel out what I'll need to do to beat the time I just put in.

So I ask myself, "Is there anything I can do to, sort of, reenact the lost Livesplit recording?" After all, you're looking at the guy who wrote SplitRP! A visual-autosplitter whose various incarnations can either analyze the recording of a run at 600+ fps, or watch your screen, live, as you play, and send start/pause/split signals to Livesplit based on what it sees. Sure I _could_ do it. But there was a problem!

I'd already saved over my old splits with the new PB. I'd need some way of recovering the old PB from the data in the LSS split file! Is it even in there? Is any of this possible?!

Yeah.
It was easy, actually.

So easy that I decided to make it a lot more complicated and expand the little script I used to restore my one lost PB run into a Python app fit for public consumption. And today I present to you...

## Restore My Splits!
- Run 'restoreMySplits.py' (Python 3.0+, i think?) and you'll be asked which file to open.
- Then, you'll be shown a list of all your (probably) restorable past runs.
  - _Some simple culling is done initially to remove obviously unrestorable attempts._
- Pick the run you want to try to restore and - if its restorable - _(the script literally repairs borked run data automatically)_ you'll be shown a list of the proposed changes to your segment PB.
- If it looks good to you, just tell us where to save the new file! _(backup your original splits first, and save to a new file entirely -- just to be safe!)_

I put 3 days into refining this ~350 line script, and I've gone fairly well overboard with it, I think. So if it tells you that the run is unrestorable, it's probably right. If there's skipped splits in your run -- no problem. If there's a single split missing for some reason -- I got you. If the sum of segments doesn't add up to the expected final time -- I can fix that! (maybe)

All these are taken care of automatically, and if there's any doubt about the accuracy of its fixes, the script will notify you before anything gets saved. But yeah... That means if it says the run is unrecoverable, it probably is.

But hey! Maybe it's a bug. There's bugs in everything. Did you know bugs come out of the pores of your face at night to eat the dead skin off your nose?

...maybe, maybe you didn't want to know that... -cough-