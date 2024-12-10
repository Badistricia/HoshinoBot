class Player:
    def __init__(self, profile_id = "", name = "", steam_id = "" , avatars = "",country = "",last_match_ID = 0, last_game_at = "",user_data= {}):
        self.profile_id = profile_id
        self.name = name
        self.steam_id = steam_id
        self.avatars = avatars
        self.country = country
        self.last_match_ID = last_match_ID
        self.last_game_at = last_game_at
        self.user_data = user_data

    def to_dict(self):
        output = {}
        output["profile_id"] = self.profile_id
        output["name"] = self.name
        output["steam_id"] = self.steam_id
        output["avatars"] = self.avatars
        output["country"] = self.country
        output["last_match_ID"] = self.last_match_ID
        output["last_game_at"] = self.last_game_at
        output["user_data"] = self.user_data

        return output

    def load_dict(self, d):
        self.profile_id = d["profile_id"]
        self.name = d["name"]
        self.steam_id = d["steam_id"]
        self.avatars = d["avatars"]
        self.country = d["country"]
        self.last_match_ID = d["last_match_ID"]
        self.last_game_at = d["last_game_at"]
        self.user_data = d["user_data"]