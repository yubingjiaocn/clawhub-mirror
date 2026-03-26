import { Link } from "react-router-dom";
import type { SkillListItem } from "../lib/api";

type SkillCardProps = {
  skill: SkillListItem;
  badge?: string | string[];
};

export function SkillCard({ skill, badge }: SkillCardProps) {
  const link = `/skills/${skill.slug}`;
  const badges = Array.isArray(badge) ? badge : badge ? [badge] : [];

  return (
    <Link to={link} className="card skill-card">
      {badges.length > 0 && (
        <div className="skill-card-tags">
          {badges.map(label => <div key={label} className="tag">{label}</div>)}
        </div>
      )}
      <h3 className="skill-card-title">{skill.displayName}</h3>
      <p className="skill-card-summary">{skill.summary || "A fresh skill bundle."}</p>
      <div className="skill-card-footer">
        <div className="stat">
          <span>&#9733; {skill.stats.stars}</span>
          <span>&#8595; {skill.stats.downloads}</span>
        </div>
      </div>
    </Link>
  );
}
