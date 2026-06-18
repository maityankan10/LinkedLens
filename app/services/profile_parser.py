def trim_profile_for_llm(profile: dict) -> dict:
    """
    Strips a raw Apify LinkedIn profile JSON down to only what the LLM needs.
    Removes all image URLs, internal IDs, UI flags, and nested metadata noise.
    
    Returns a clean, compact dict ready to be serialized and sent to the LLM.
    """

    def _trim_experience(exp: dict) -> dict:
        return {
            "title": exp.get("position"),
            "company": exp.get("companyName"),
            "duration": exp.get("duration"),
            "employment_type": exp.get("employmentType"),
            "description": (exp.get("description") or "")[:400],
            "skills": exp.get("skills", []),
        }

    def _trim_education(edu: dict) -> dict:
        return {
            "school": edu.get("schoolName"),
            "degree": edu.get("degree"),
            "field": edu.get("fieldOfStudy"),
            "period": edu.get("period"),
        }

    def _trim_certification(cert: dict) -> dict:
        return {
            "title": (cert.get("title") or "").strip(),
            "issued_by": cert.get("issuedBy"),
            "issued_at": cert.get("issuedAt"),
        }

    def _trim_honor(honor: dict) -> dict:
        return {
            "title": honor.get("title"),
            "issued_by": honor.get("issuedBy"),
            "issued_at": honor.get("issuedAt"),
            "description": honor.get("description"),
        }

    def _trim_project(project: dict) -> dict:
        return {
            "title": project.get("title"),
            "duration": project.get("duration"),
            "description": project.get("description"),
        }

    def _trim_publication(pub: dict) -> dict:
        return {
            "title": pub.get("title"),
            "published_at": pub.get("publishedAt"),
        }

    def _trim_volunteering(vol: dict) -> dict:
        return {
            "role": vol.get("role"),
            "organization": vol.get("organizationName"),
            "cause": vol.get("cause"),
            "duration": vol.get("duration"),
        }

    # --- Main extraction ---
    return {
        # Core identity
        "name": f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip(),
        "headline": profile.get("headline"),
        "about": profile.get("about"),
        "location": profile.get("location", {}).get("linkedinText"),

        # Audience signals
        "follower_count": profile.get("followerCount"),
        "connections_count": profile.get("connectionsCount"),

        # Profile type signals
        "is_creator": profile.get("creator", False),
        "is_influencer": profile.get("influencer", False),
        "is_premium": profile.get("premium", False),
        "open_to_work": profile.get("openToWork", False),

        # Professional context
        "top_skills": profile.get("topSkills"),
        "current_position": [
            _trim_experience(exp)
            for exp in profile.get("currentPosition", [])
        ],
        "experience": [
            _trim_experience(exp)
            for exp in profile.get("experience", [])
        ],
        "education": [
            _trim_education(edu)
            for edu in profile.get("education", [])
        ],

        # Skills
        "skills": [
            s.get("name") for s in profile.get("skills", []) if s.get("name")
        ],

        # Credibility boosters
        "certifications": [
            _trim_certification(c)
            for c in profile.get("certifications", [])
        ],
        "honors_and_awards": [
            _trim_honor(h)
            for h in profile.get("honorsAndAwards", [])
        ],
        "publications": [
            _trim_publication(p)
            for p in profile.get("publications", [])
        ],
        "projects": [
            _trim_project(p)
            for p in profile.get("projects", [])
        ],
        "volunteering": [
            _trim_volunteering(v)
            for v in profile.get("volunteering", [])
        ],

        # Soft signals
        "languages": [
            f"{l.get('name')} ({l.get('proficiency')})"
            for l in profile.get("languages", [])
            if l.get("name")
        ],
        "causes": profile.get("causes", []),
    }


def extract_display_info(profile: dict) -> dict:
    """
    Extracts only what the API response needs for the frontend display.
    Separate from LLM trimming — this is for LinkedInAnalyzeResponse.
    """
    return {
        "name": f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip(),
        "headline": profile.get("headline", ""),
        "location": profile.get("location", {}).get("linkedinText"),
        "profile_picture": profile.get("photo"),
        "follower_count": profile.get("followerCount", 0),
    }