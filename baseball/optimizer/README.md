# optimizer

To simulate entire season and ouput predicted stats, run (default year is 2014):

```
python -m baseball.optimizer.validator --num_simulations=100 --year=2014
```

To backtest the optimizer over a season, run (default year is 2014):

```
python -m baseball.optimizer.backtest --num_simulations=200 --year=2014
```

To simulate the optimizer over a given day, run (default num_lineups is 3,
resimulate=true):

```
python -m baseball.optimizer.optimizer --date=0904 --num_simulations=200 --num_lineups=90
```

The default is `resimulate=true` which simulates out the games and optimizes as
specified. If `resimulate=false` then the predictions from the last time
optimizer has been run are used. This allows the optimizer to run much faster
if all you care about is changing the custom_score_adjustments.
NOTE: this doesn't check that the last optimizer run was for the same date and
number of simulations. To avoid this mistake delete the `.pickle` files in the
optimizer folder when done with a session.

Optimizer then writes out to `predicted_lineups_<date>_<num_sims>sims.csv`. The
more ambiguous columns are:
- `custom DK pts pred`: The custom player adjustments for the optimizer
- `DK pts pred`: Predictions from the simulator. This includes custom player
  rate adjustments but not the custom score multipliers used to express
preferences for the optimizer.
- `custom pred total`: The optimizer uses the custom player adjustments. This
  is the adjusted lineup score the optimizer was working with.
- `pred total`: Undoing the player score adjustments this is the projected
  total lineup score. Note that this does not undo any custom player rate
adjustments.
- `pred var`: The predicted covariance of the lineup total dk score.
- `maj_stack`: For example if the Yankees is the most common team for this
  lineup then this is the number of players in the lineup on the Yankees.
- `min_stack`: Same as maj_stack but for the second most common team.

Optimizer also writes out to
`predicted_playerscores_<date>_<num_sims>sims.csv`. Columns track the player
rates actually plugged into the simulator, the predicted statistics outputted
by the simulator, and some other info like team_id and predicted dk scores.
NOTE: custom pts per Dollar is for custom DK pts pred not DK pts pred.
