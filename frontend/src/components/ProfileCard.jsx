function ProfileCard({ profile }) {
  const { name, headline, location, profile_picture, follower_count, insights } = profile;
  const score = insights?.profile_score;

  return (
    <div className="pc">
      <div className="pc-banner" />
      <div className="pc-body">
        <div className="pc-avatar-row">
          <div className="pc-avatar">
            {profile_picture
              ? <img src={profile_picture} alt={name} />
              : <span>{name?.[0] ?? "?"}</span>
            }
          </div>
          {score != null && (
            <div className="pc-score">
              <span className="pc-score-num">{score}</span>
              <span className="pc-score-label">Profile Score</span>
            </div>
          )}
        </div>

        <h2 className="pc-name">{name}</h2>
        {headline && <p className="pc-headline">{headline}</p>}

        <div className="pc-meta">
          {location && <span>{location}</span>}
          {follower_count > 0 && (
            <span>{follower_count.toLocaleString()} followers</span>
          )}
        </div>

        {insights?.profile_summary && (
          <p className="pc-summary">{insights.profile_summary}</p>
        )}
      </div>
    </div>
  );
}

export default ProfileCard;
