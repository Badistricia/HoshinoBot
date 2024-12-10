class CivStatus:
    def __init__(self, win_rate, pick_rate, win_count, loss_count, games_count, civilization, rating_group,
                 duration_median, duration_average, duration_maximum, duration_minimum, player_games_count,
                 duration_percentile95):
        self.win_rate = win_rate
        self.pick_rate = pick_rate
        self.win_count = win_count
        self.loss_count = loss_count
        self.games_count = games_count
        self.civilization = civilization
        self.rating_group = rating_group
        self.duration_median = duration_median
        self.duration_average = duration_average
        self.duration_maximum = duration_maximum
        self.duration_minimum = duration_minimum
        self.player_games_count = player_games_count
        self.duration_percentile95 = duration_percentile95