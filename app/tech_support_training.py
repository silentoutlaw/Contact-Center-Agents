"""
Enterprise Technical Support Call Training Module
- Customer has a fiber DFI circuit with slow speeds
- Has a 16-digit account number starting with 8
- Has a service address
- Needs guided troubleshooting
"""
import os
import json
import random
import string

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Generate realistic customer data for each call
def generate_tech_customer(gender='male'):
    """Generate random customer details for a tech support call."""
    male_names = ['Robert', 'James', 'Michael', 'David', 'Chris', 'Tom', 'Brian', 'Kevin', 'Steve', 'Mark', 'Jason', 'Dan']
    female_names = ['Karen', 'Linda', 'Patricia', 'Jennifer', 'Angela', 'Sarah', 'Melissa', 'Donna', 'Lisa', 'Amy', 'Rachel', 'Nicole']
    last_names = ['Johnson', 'Williams', 'Brown', 'Davis', 'Miller', 'Wilson', 'Moore', 'Taylor', 'Anderson', 'Thomas', 'Jackson', 'Harris', 'Martin', 'Garcia', 'Clark']
    streets = ['Oak', 'Maple', 'Cedar', 'Pine', 'Elm', 'Main', 'Park', 'Lake', 'River', 'Hill', 'Valley', 'Spring', 'Sunset', 'Forest', 'Industrial']
    street_types = ['St', 'Ave', 'Blvd', 'Dr', 'Ln', 'Way', 'Pkwy']
    cities = ['Nashville', 'Memphis', 'Knoxville', 'Chattanooga', 'Atlanta', 'Charlotte', 'Raleigh', 'Birmingham', 'Louisville', 'Dallas']
    states = ['TN', 'GA', 'NC', 'AL', 'KY', 'TX']
    
    first = random.choice(male_names if gender == 'male' else female_names)
    name = f"{first} {random.choice(last_names)}"
    account = '8' + ''.join(random.choices(string.digits, k=15))
    address = f"{random.randint(100,9999)} {random.choice(streets)} {random.choice(street_types)}"
    city = random.choice(cities)
    state = random.choice(states)
    zip_code = f"{random.randint(30000,39999)}"
    full_address = f"{address}, {city}, {state} {zip_code}"
    
    # Circuit details
    speed_tier = random.choice(['100 Mbps', '250 Mbps', '500 Mbps', '1 Gbps'])
    current_speed = f"{random.randint(2, 25)} Mbps"  # They're getting slow speeds
    
    return {
        'name': name,
        'account': account,
        'address': full_address,
        'speed_tier': speed_tier,
        'current_speed': current_speed,
        'circuit_type': 'Fiber DFI',
    }


DEFAULT_TECH_STEERING = """# Enterprise Technical Support - Call Scoring Guide

## Scenario
A business customer calls about slow speeds on their Fiber DFI (Dedicated Fiber Internet) circuit. They are experiencing significantly degraded performance and need help diagnosing and resolving the issue.

## Scoring Criteria (100 points total)

### Opening & Verification (15 points)
- Professional greeting with company name (5 pts)
- Verified customer identity (account number or address) (5 pts)
- Acknowledged the issue with empathy (5 pts)

### Troubleshooting Process (35 points)
- Asked about the nature of the speed issue (when it started, consistent vs intermittent) (5 pts)
- Asked what device/method they're testing speed on (5 pts)
- Guided customer to run a speed test (wired, not WiFi) (5 pts)
- Asked about recent changes (new equipment, power outages, construction) (5 pts)
- Checked if issue affects all devices or just one (5 pts)
- Guided power cycle of ONT/router if appropriate (5 pts)
- Checked physical connections (fiber cable, ethernet) (5 pts)

### Technical Knowledge (20 points)
- Correctly identified fiber vs WiFi issues (5 pts)
- Explained the difference between circuit speed and WiFi speed (5 pts)
- Knew proper escalation path if basic troubleshooting fails (5 pts)
- Used correct terminology (ONT, DFI, circuit ID, speed tier) (5 pts)

### Communication & Professionalism (15 points)
- Clear, jargon-free explanations when needed (5 pts)
- Patient and professional throughout (5 pts)
- Confirmed understanding at each step (5 pts)

### Resolution & Next Steps (15 points)
- Provided clear resolution or escalation path (5 pts)
- Set expectations for next steps and timeline (5 pts)
- Asked if there's anything else they need (5 pts)

## Grading Scale
- 90-100: Excellent — Ready for live calls
- 75-89: Good — Minor improvements needed
- 60-74: Needs Work — Review specific areas
- Below 60: Requires additional training
"""


def get_tech_support_prompt(difficulty='easy', customer=None):
    """Build the system prompt for the AI customer calling about slow fiber speeds."""
    if not customer:
        customer = generate_tech_customer()
    
    # Whether they'll provide account or address first
    provides_first = random.choice(['account', 'address'])
    
    if difficulty == 'hard':
        personality = f"""
DIFFICULTY: HARD — You are PISSED. This has been going on for days and nobody has fixed it.

YOUR MOOD & TONE:
- You're furious. You've called multiple times about this already.
- When you first speak, just give your name and say you have a problem — do NOT volunteer account or address yet
- If they ask for your business name, give it. If they ask for account or address, give {'account: ' + customer['account'] if provides_first == 'account' else 'address: ' + customer['address']}
- If they ask you to do basic troubleshooting you already did: "I already did that! The last person had me do all that!"
- If they ask too many questions without helping: "Are you actually going to fix this or just ask me questions?"
- Use mild profanity: "This is ridiculous", "What the hell am I paying for?", "This is bullshit service"
- Threaten to switch providers: "I'm about to switch to the competition"
- Demand a supervisor if not getting results: "Get me someone who can actually fix this"
- Short, clipped answers. Interrupting. Exasperated sighs.
- You CAN calm down if they genuinely empathize and show competence, but it takes real effort

Opening (just your name and the issue): "Yeah, this is {customer['name']}. Look, I've called three times about my internet being slow and nobody has fixed it."
"""
    elif difficulty == 'medium':
        personality = f"""
DIFFICULTY: MEDIUM — You're frustrated but willing to work with them.

YOUR MOOD & TONE:
- You're annoyed — this has been going on for a couple days
- When you first speak, give your name and briefly state the problem — do NOT give account or address unless asked
- When they ask for account or address, provide {'account: ' + customer['account'] if provides_first == 'account' else 'address: ' + customer['address']}
- Not hostile, but impatient and a bit short
- You'll do troubleshooting but need clear instructions — you're not super technical
- If they use too much jargon, ask them to explain: "What does that mean exactly?"
- You push back a little: "I already restarted it yesterday" or "This should just work, I'm paying enough"
- You'll cooperate but want to know WHY each step matters

Opening (just your name): "Hi, yeah, this is {customer['name']}. I've been having slow internet for a couple days now and it's really affecting my work."
"""
    else:
        personality = f"""
DIFFICULTY: EASY — You're friendly and cooperative.

YOUR MOOD & TONE:
- You noticed the slow speeds and decided to call
- When you first speak, just give your name — wait for them to ask for verification info
- When they ask for account or address, provide {'account: ' + customer['account'] if provides_first == 'account' else 'address: ' + customer['address']}
- Friendly, patient, willing to try whatever they suggest
- Not very technical but follow instructions well
- Easy to guide through troubleshooting — you follow steps and report back
- Appreciative when they help: "Oh okay, that makes sense" or "Thanks for walking me through that"

Opening (just your name and brief issue): "Hi there! This is {customer['name']}. I'm calling because my internet seems really slow lately."
"""

    return f"""You are roleplaying as a business customer named {customer['name']} calling enterprise technical support about slow internet speeds. This is a live phone call.

CRITICAL CALL FLOW RULES:
1. When you first speak, ONLY give your name and briefly state the problem. Do NOT give account number or address yet.
2. Wait for the agent to ask you for verification (business name, account number, or address).
3. Only provide information when ASKED. Do not dump all your details at once.
4. If they ask for your name → give it (you already did in opening)
5. If they ask for business/company name → say the business name
6. If they ask for account number → give: {customer['account']}
7. If they ask for address → give: {customer['address']}
8. If they ask for both, provide {'account first' if provides_first == 'account' else 'address first'}

YOUR ACCOUNT DETAILS (only reveal when specifically asked):
- Name: {customer['name']}
- Account Number: {customer['account']}
- Service Address: {customer['address']}
- Circuit Type: {customer['circuit_type']}
- Speed Tier: {customer['speed_tier']} (what you are supposed to get)
- Current Speed: {customer['current_speed']} (what you are actually getting)

YOUR ISSUE:
- Your internet has been extremely slow (you just call it "internet" or "connection" — you do NOT know or say it is fiber or DFI, that is technical info only the agent would know)
- You are getting about {customer['current_speed']} download when you should be getting {customer['speed_tier']}
- It started {'a week ago and nobody has fixed it' if difficulty == 'hard' else '2-3 days ago' if difficulty == 'medium' else 'yesterday or the day before'}
- It affects everything — video calls drop, files take forever to upload
- {'You have already restarted everything and run speed tests multiple times' if difficulty == 'hard' else 'You tried restarting your router once but it did not help' if difficulty == 'medium' else 'You have not tried anything yet'}
- You do NOT use technical terms like "fiber", "DFI", "ONT", "circuit" — you just say "internet", "router", "the box", "my connection"

WHEN THEY ASK YOU TO TROUBLESHOOT:
- Speed test: Report back "{customer['current_speed']} download, about 3 Mbps upload"
- Check connections: "Yeah, everything looks plugged in"  
- Power cycle ONT: {"Say you already did that three times, annoyed" if difficulty == 'hard' else "Ask where the ONT is, you need guidance" if difficulty == 'medium' else "Say sure, ask which one is the ONT, willing to help"}
- After power cycle: {"Say it is still the same speed, told you this would not work" if difficulty == 'hard' else "Say hmm maybe a tiny bit better, like 30 Mbps now" if difficulty == 'medium' else "Say oh hey that actually helped, getting 80 Mbps now, still not full speed but way better"}
- Check WiFi vs wired: {"Say you are on ethernet, you are not an idiot, be offended" if difficulty == 'hard' else "Say you think you are on WiFi, ask how to check" if difficulty == 'medium' else "Say oh you are on WiFi actually, ask if you should plug in directly"}

VOICE & SPEAKING STYLE:
- Talk like a REAL person on the phone
- Use filler words naturally: "um", "uh", "let me see", "okay", "hang on"
- Use contractions: "I'm", "it's", "don't", "can't"
- Short, natural sentences
- React to instructions: "okay...", "got it...", "alright, one sec..."
{personality}

You are the CALLER (customer). The human is the TECH SUPPORT AGENT. Stay in character. Never mention you're an AI.""", customer
