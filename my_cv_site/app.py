from flask import Flask, render_template

app = Flask(__name__)

cv = {
    "name": "Nikolai Sergeev",
    "title": "Product Owner",
    "contact": {
        # phone and email omitted to keep them private
        "github": "https://github.com/fatalexception",
        "linkedin": "https://www.linkedin.com/in/fatalexception/",
        "location": "Thessaloniki, Greece",
    },
    "profile": (
        "An experienced product owner with a wide expertise in marketing and digital,\n"
        "continuously looking for challenges and interesting projects. At the current place of work,\n"
        "the main priority for me is effective management of the team, based on the principles of leadership.\n"
        "My strengths: critical thinking, creativity, ability to negotiate and find compromises,\n"
        "technical background, and love to product management challenges. In my product approach\n"
        "I focus on data-driven decisions, testing hypothesis through MVP and flexibility."
    ),
    "skills": {
        "hard": [
            "Market Research",
            "A/B Testing",
            "Cohort Analysis",
            "Product Roadmap Development",
            "Agile Methodology",
            "SAFe",
            "OKR",
            "Data-driven Decision Making",
            "Defining MVPs and Prototypes",
            "Product Metrics",
            "Jira",
            "Confluence",
            "Trello",
            "Miro",
            "Tableau",
            "Figma",
            "Microsoft Excel",
            "Python",
            "SQL",
        ],
        "soft": [
            "Strategic Thinking",
            "Communication Skills",
            "Teamwork",
            "Leadership",
            "Practicing Empathy",
            "Flexibility",
            "Active Listening",
            "Critical Thinking",
            "Positive Attitude",
        ],
        "languages": {
            "English": "C1",
            "Russian": "Native",
        },
    },
    "experience": [
        {
            "role": "Product Owner (T-Digital by Deutsche Telekom)",
            "period": "Nov 2020 — Present",
            "details": [
                (
                    "As part of the Gigabit project, oversee the development and support of products "
                    "in the OS&R and Fiberbau domains."
                ),
                (
                    "Collaboratively lead a multidisciplinary team alongside the Scrum Master: "
                    "five Backend Developers, two Business Analysts, three QA Engineers."
                ),
                (
                    "Initiated a critical revision of the ONT Usage Support UI after thorough incident analysis, "
                    "simplifying incident management to great customer acclaim."
                ),
                (
                    "Facilitated the rapid transition of knowledge and responsibility for the product "
                    "from external contractors to the internal team."
                ),
            ],
        },
        {
            "role": "Product Owner (X5 Group)",
            "period": "Nov 2020 — Sep 2022",
            "details": [
                (
                    "Launched 600+ A/B experiments for CVM campaigns to increase the incremental GMV "
                    "by 5.5 B RUB yearly."
                ),
                (
                    "Designed and implemented automated onboarding chain for new customers to raise "
                    "retention from 42% to 44%."
                ),
                (
                    "Led a team of Data Science developers, Data Analysts, Quality Engineer, Marketing "
                    "Manager, Designer, Commerce Manager using OKR & Scrum."
                ),
                "Communicated requirements and deadlines to stakeholders through discovery and delivery processes.",
            ],
        },
        {
            "role": "Head of CRM Marketing (Citymobil, Mail.ru Group)",
            "period": "Sep 2019 — Nov 2020",
            "details": [
                (
                    "Planned and executed a referral program, decreasing CAC by 3× versus performance "
                    "marketing."
                ),
                (
                    "Performed RFM analysis and anti-churn/onboarding campaigns to boost GMV by 600 M RUB yearly."
                ),
                (
                    "Collaborated on loyalty program development with mobile app PMs and analytics team."
                ),
                "Defined business requirements for integration with the customer data platform.",
            ],
        },
    ],
    "education": [
        {
            "institution": "Bauman Moscow State Technical University",
            "period": "2002 — 2006",
            "degree": "Machines and technologies for metal forming",
        }
    ],
    "courses": [
        "2021 – A/B-testing and mathematical statistics (EXPF)",
        "2017 – Python as a First Programming Language (Higher School of Economics)",
    ],
}


@app.route("/")
def index():
    return render_template("index.html", cv=cv)


if __name__ == "__main__":
    app.run(debug=True)
