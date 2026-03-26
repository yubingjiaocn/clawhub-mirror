import { Link } from "react-router-dom";
import type { Skill } from "../lib/api";

type SkillCardProps = {
  skill: Skill;
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
          <span>★ {skill.stars}</span>
          <span>↓ {skill.downloads}</span>
        </div>
      </div>
    </Link>
  );
}
