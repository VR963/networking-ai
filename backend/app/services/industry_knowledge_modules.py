class IndustryKnowledge:
    """Pre-loaded industry expertise modules.

    Each module contains domain-specific knowledge so agents can speak
    the language of the industry before meeting users.
    """

    MODULES = {
        "technology": {
            "key_roles": [
                "Software Engineer", "Product Manager", "Data Scientist",
                "DevOps Engineer", "UX Designer", "Engineering Manager",
                "CTO", "VP Engineering", "Staff Engineer", "Principal Engineer",
            ],
            "skill_benchmarks": {
                "junior": "0-2 years, foundational skills, learning rapidly",
                "mid": "3-5 years, independent contributor, mentoring juniors",
                "senior": "5-8 years, system design, cross-team impact",
                "staff": "8-12 years, org-wide impact, technical strategy",
                "principal": "12+ years, industry influence, architecture vision",
            },
            "culture_signals": [
                "remote-first vs office culture",
                "startup pace vs enterprise stability",
                "IC track vs management track",
                "open source contributions",
                "conference speaking",
            ],
            "hidden_criteria": [
                "tech stack preferences often mask deeper values",
                "company size preference reveals risk tolerance",
                "remote preference may indicate family priorities",
            ],
        },
        "finance": {
            "key_roles": [
                "Financial Analyst", "Investment Banker", "Portfolio Manager",
                "Risk Analyst", "CFO", "Quantitative Analyst", "Trader",
                "Compliance Officer", "Wealth Manager", "Actuary",
            ],
            "skill_benchmarks": {
                "analyst": "0-3 years, modeling, due diligence",
                "associate": "3-6 years, deal execution, client management",
                "vp": "6-10 years, origination, team leadership",
                "director": "10-15 years, P&L responsibility, strategy",
                "md": "15+ years, rainmaking, firm leadership",
            },
            "culture_signals": [
                "work-life balance expectations",
                "buy-side vs sell-side preference",
                "regulatory environment comfort",
                "quantitative vs relationship-driven",
            ],
            "hidden_criteria": [
                "compensation structure preference reveals career stage",
                "firm prestige sensitivity indicates social motivations",
                "hours tolerance reveals life priorities",
            ],
        },
        "healthcare": {
            "key_roles": [
                "Physician", "Nurse Practitioner", "Healthcare Administrator",
                "Clinical Research Director", "Biotech Scientist",
                "Health Informatics Specialist", "Medical Director",
                "Pharmaceutical Manager", "Public Health Director",
            ],
            "skill_benchmarks": {
                "resident": "Training phase, supervised practice",
                "attending": "Independent practice, specialization",
                "director": "Department leadership, policy influence",
                "chief": "Organization-wide impact, strategy",
            },
            "culture_signals": [
                "academic vs private practice",
                "patient volume vs quality time",
                "research vs clinical focus",
                "urban vs rural setting",
            ],
            "hidden_criteria": [
                "call schedule tolerance reveals family priorities",
                "academic affiliation desire indicates prestige needs",
                "patient population preference reveals values",
            ],
        },
        "legal": {
            "key_roles": [
                "Associate Attorney", "Partner", "General Counsel",
                "Legal Director", "Compliance Director", "Judge",
                "Legal Tech Specialist", "IP Attorney", "Litigation Partner",
            ],
            "skill_benchmarks": {
                "junior_associate": "0-3 years, research, drafting",
                "senior_associate": "4-7 years, client management, strategy",
                "counsel": "7-10 years, specialization, business development",
                "partner": "10+ years, origination, firm leadership",
            },
            "culture_signals": [
                "biglaw vs boutique vs in-house",
                "billable hour targets",
                "pro bono commitment",
                "litigation vs transactional",
            ],
            "hidden_criteria": [
                "firm size preference reveals autonomy needs",
                "practice area passion indicates purpose-driven career",
                "partnership track interest reveals long-term ambition",
            ],
        },
        "hr": {
            "key_roles": [
                "HR Manager", "Talent Acquisition Director", "CHRO",
                "People Operations Manager", "Compensation Analyst",
                "Learning & Development Director", "HR Business Partner",
                "Diversity & Inclusion Director", "Employee Relations Manager",
            ],
            "skill_benchmarks": {
                "coordinator": "0-2 years, process management, compliance basics",
                "manager": "3-6 years, team leadership, program ownership",
                "director": "7-12 years, strategy, executive partnership",
                "vp_chro": "12+ years, board-level, organizational design",
            },
            "culture_signals": [
                "people-first vs business-first HR philosophy",
                "data-driven vs intuition-driven decisions",
                "startup scaling vs enterprise optimization",
                "employee advocacy vs management alignment",
            ],
            "hidden_criteria": [
                "company stage preference reveals comfort with ambiguity",
                "industry focus indicates passion areas",
                "HR tech adoption reveals innovation mindset",
            ],
        },
    }

    def get_module(self, industry: str) -> dict:
        normalized = industry.lower().strip()
        return self.MODULES.get(normalized, self._general_module())

    def _general_module(self) -> dict:
        return {
            "key_roles": [],
            "skill_benchmarks": {},
            "culture_signals": [],
            "hidden_criteria": [
                "Career transition patterns reveal adaptability",
                "Industry choice reveals values alignment",
            ],
        }

    def list_industries(self) -> list[str]:
        return list(self.MODULES.keys())


industry_knowledge = IndustryKnowledge()
