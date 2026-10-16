import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path


@dataclass
class GoldenQAPair:
    id: str
    domain: str
    query: str
    ground_truth_answer: str
    expected_sources: List[str]
    expected_evidence_keywords: List[str]
    is_answerable: bool = True
    tenant_id: str = "student_benchmark"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "query": self.query,
            "ground_truth_answer": self.ground_truth_answer,
            "expected_sources": self.expected_sources,
            "expected_evidence_keywords": self.expected_evidence_keywords,
            "is_answerable": self.is_answerable,
            "tenant_id": self.tenant_id,
        }


# Curated corpus documents containing ground truth information
BENCHMARK_CORPUS_DOCUMENTS = {
    "physics_mechanics.pdf": (
        "Newton's first law states that an object remains at rest or in uniform motion in a straight line unless acted upon by a net external force. "
        "Newton's second law quantifies force as the time rate of change of momentum, expressed as F = dp/dt, which simplifies to F = ma for constant mass. "
        "Newton's third law states that for every action force, there is an equal and opposite reaction force acting on different interacting bodies. "
        "Work done by a force is defined as the line integral W = integral(F . dr). The work-energy theorem states that net work done on a particle equals change in kinetic energy: W_net = Delta K. "
        "Conservative forces have the property that work done is path-independent and the line integral around any closed loop is zero. "
        "Potential energy U is defined for conservative forces such that F = -grad(U). Total mechanical energy E = K + U remains conserved in isolated systems with no non-conservative work. "
        "Linear momentum p = mv is conserved in closed systems where external force Sigma F_ext = 0. In elastic collisions, both kinetic energy and momentum are conserved. In inelastic collisions, kinetic energy is lost. "
        "Centripetal acceleration for circular motion of radius r at tangential speed v is given by a_c = v^2 / r, directed radially inward toward the center of curvature. "
        "Angular momentum L for a rigid body rotating with moment of inertia I about a fixed axis is L = I * omega. Torque is the rate of change of angular momentum: tau = dL/dt. "
        "Simple harmonic motion occurs when restoring force is proportional to displacement: F = -kx. The angular frequency is omega = sqrt(k/m) and period T = 2*pi*sqrt(m/k)."
    ),
    "physics_thermodynamics.pdf": (
        "The zeroth law of thermodynamics defines thermal equilibrium and establishes temperature as a state variable: if A is in equilibrium with B, and B with C, A is in equilibrium with C. "
        "The first law of thermodynamics states energy conservation: Delta U = Q - W, where Delta U is internal energy change, Q is heat added, and W is work done by the system. "
        "For an ideal gas, PV = nRT. In an isothermal process, temperature remains constant and Delta U = 0, so Q = W = nRT * ln(V_f / V_i). "
        "In an adiabatic process, no heat is exchanged (Q = 0), and P * V^gamma = constant, where gamma = C_p / C_v is the heat capacity ratio. "
        "The second law of thermodynamics introduces entropy S: in any spontaneous natural process, the total entropy of an isolated system always increases (Delta S >= 0). "
        "Carnot heat engine efficiency is the maximum theoretical efficiency between hot reservoir T_h and cold reservoir T_c: eta_carnot = 1 - (T_c / T_h). "
        "The third law of thermodynamics states that the entropy of a pure crystalline substance approaches zero as temperature approaches absolute zero (0 Kelvin)."
    ),
    "biology_genetics.pdf": (
        "DNA is a double-stranded helix composed of nucleotide monomers containing deoxyribose sugar, phosphate, and one of four nitrogenous bases: adenine, thymine, guanine, and cytosine. "
        "According to Chargaff's rules and Watson-Crick pairing, Adenine pairs with Thymine via two hydrogen bonds (A=T), and Guanine pairs with Cytosine via three hydrogen bonds (G=C). "
        "DNA replication is semiconservative: DNA helicase unwinds the double helix, primase synthesizes RNA primers, and DNA polymerase III synthesizes the leading and lagging strands in the 5' to 3' direction. "
        "The central dogma of molecular biology describes information flow: DNA is transcribed into mRNA by RNA polymerase, and mRNA is translated into polypeptides by ribosomes. "
        "During transcription, RNA polymerase binds to the promoter sequence (TATA box), initiates mRNA elongation, and terminates at polyadenylation signals. "
        "During translation, transfer RNA (tRNA) molecules carry specific amino acids matching mRNA codons via complementary anticodons. The start codon AUG codes for methionine. "
        "Mendel's law of segregation states that alleles separate during gamete formation so each gamete carries only one allele. Mendel's law of independent assortment states alleles of different genes segregate independently. "
        "Mutations can be point mutations (missense, nonsense, silent) or frameshift mutations resulting from insertions or deletions not divisible by three."
    ),
    "biology_cell_biology.pdf": (
        "The cell is the basic structural and functional unit of all living organisms. Prokaryotic cells lack membrane-bound organelles and a true nucleus, while eukaryotic cells possess compartmentalized organelles. "
        "The plasma membrane follows the fluid mosaic model, consisting of an amphipathic phospholipid bilayer with embedded integral and peripheral proteins, cholesterol, and carbohydrates. "
        "Mitochondria are the powerhouses of the cell, generating adenosine triphosphate (ATP) via cellular respiration: glycolysis, Krebs cycle, and oxidative phosphorylation. "
        "The endosymbiotic theory posits that mitochondria and chloroplasts originated as free-living prokaryotes engulfed by ancestral eukaryotic host cells. "
        "Endoplasmic reticulum occurs in two forms: rough ER with ribosomes for secretory protein synthesis, and smooth ER for lipid synthesis, carbohydrate metabolism, and calcium storage. "
        "The Golgi apparatus consists of flattened cisternae that modify, sort, and package proteins received from the rough ER for transport to destinations or secretion. "
        "Lysosomes contain hydrolytic acid hydrolases with an optimum pH of approximately 4.5-5.0 for autophagy and degradation of cellular waste."
    ),
    "cs_algorithms.pdf": (
        "Big-O notation describes the asymptotic upper bound of an algorithm's execution time or space complexity as input size n grows to infinity. "
        "Quicksort is a divide-and-conquer sorting algorithm with average-case time complexity O(n log n) and worst-case O(n^2) when an unbalanced pivot is chosen. "
        "Mergesort is a stable divide-and-conquer algorithm with guaranteed O(n log n) time complexity in all cases, requiring O(n) auxiliary space. "
        "Binary search algorithm locates a target value in a sorted array in O(log n) time by repeatedly dividing the search interval in half. "
        "Dijkstra's algorithm finds single-source shortest paths in weighted graphs with non-negative edge weights using a priority queue in O((V + E) log V) time. "
        "Dynamic programming solves complex problems by breaking them down into overlapping subproblems with optimal substructure, utilizing memoization or tabulation. "
        "Hash tables provide average-case O(1) time complexity for lookup, insertion, and deletion operations, with collision resolution via separate chaining or open addressing."
    ),
    "cs_operating_systems.pdf": (
        "An operating system acts as an intermediary between computer hardware and user applications, managing CPU scheduling, memory, storage, and I/O devices. "
        "A process is a program in execution containing program counter, stack, and data section. A thread is a lightweight unit of CPU execution sharing memory with peer threads in the same process. "
        "CPU scheduling algorithms include First-Come First-Served (FCFS), Shortest Job First (SJF), Round Robin (RR) with time quantum, and Multi-Level Feedback Queues. "
        "Deadlock is a condition where a set of processes are blocked because each holds a resource and waits for another. Coffman's four conditions are mutual exclusion, hold and wait, no preemption, and circular wait. "
        "Virtual memory uses paging to map virtual addresses to physical frames via page tables. The Translation Lookaside Buffer (TLB) is a fast hardware cache that accelerates page table lookups. "
        "Page replacement algorithms include Least Recently Used (LRU), First-In First-Out (FIFO) which can suffer from Belady's anomaly, and the optimal algorithm (OPT)."
    ),
    "math_linear_algebra.pdf": (
        "A vector space V over a field F is a set closed under vector addition and scalar multiplication satisfying eight standard axioms including associativity and distributivity. "
        "A set of vectors is linearly independent if the only linear combination yielding the zero vector has all scalar coefficients equal to zero. "
        "The rank of a matrix is the dimension of the vector space spanned by its columns (or rows). The Rank-Nullity Theorem states that for m x n matrix A: rank(A) + nullity(A) = n. "
        "An eigenvalue lambda and eigenvector v of square matrix A satisfy Av = lambda * v with v != 0. Eigenvalues are roots of the characteristic polynomial det(A - lambda * I) = 0. "
        "A matrix is diagonalizable if and only if it has n linearly independent eigenvectors. Symmetric matrices are orthogonally diagonalizable: A = Q * Lambda * Q^T. "
        "Singular Value Decomposition (SVD) factors any m x n matrix into A = U * Sigma * V^T, where U and V are orthogonal matrices and Sigma contains singular values."
    ),
    "math_calculus.pdf": (
        "The derivative f'(x) represents the instantaneous rate of change of f at x, formally defined as the limit of [f(x+h) - f(x)] / h as h approaches 0. "
        "The Fundamental Theorem of Calculus links differentiation and integration: if F'(x) = f(x), then integral from a to b of f(x) dx = F(b) - F(a). "
        "The chain rule for differentiating composite functions states that d/dx[f(g(x))] = f'(g(x)) * g'(x). "
        "Taylor's theorem states that any sufficiently differentiable function can be approximated near a point a by a polynomial sum: f(x) = sum [f^(n)(a) / n!] * (x - a)^n. "
        "A function f is continuous at x = c if the limit as x approaches c of f(x) exists, f(c) is defined, and lim(x->c) f(x) = f(c). "
        "The mean value theorem guarantees that for a continuous function on [a,b] differentiable on (a,b), there exists c in (a,b) where f'(c) = [f(b) - f(a)] / (b - a)."
    ),
}


def build_golden_dataset() -> List[GoldenQAPair]:
    """Build the comprehensive 105-question benchmark dataset."""
    questions: List[GoldenQAPair] = []

    # 1. Physics - Mechanics (12 questions)
    physics_mech = [
        ("PHYS-001", "What is Newton's first law of motion?", "An object remains at rest or in uniform straight-line motion unless acted upon by a net external force.", ["physics_mechanics.pdf"], ["first law", "rest", "uniform motion", "net external force"]),
        ("PHYS-002", "How is force defined in Newton's second law?", "Force is the time rate of change of momentum (F = dp/dt), which reduces to F = ma for constant mass.", ["physics_mechanics.pdf"], ["second law", "dp/dt", "F = ma", "momentum"]),
        ("PHYS-003", "State Newton's third law of motion.", "Every action force has an equal and opposite reaction force acting on different interacting bodies.", ["physics_mechanics.pdf"], ["third law", "action", "reaction", "equal and opposite"]),
        ("PHYS-004", "What does the work-energy theorem state?", "The net work done on a particle equals the change in its kinetic energy: W_net = Delta K.", ["physics_mechanics.pdf"], ["work-energy theorem", "kinetic energy", "net work"]),
        ("PHYS-005", "What is a conservative force?", "A force for which work done is path-independent and the closed loop line integral is zero.", ["physics_mechanics.pdf"], ["conservative forces", "path-independent", "closed loop"]),
        ("PHYS-006", "What is the relationship between potential energy and conservative force?", "Force is the negative gradient of potential energy: F = -grad(U).", ["physics_mechanics.pdf"], ["potential energy", "F = -grad(U)", "gradient"]),
        ("PHYS-007", "Under what condition is linear momentum conserved?", "When the net external force on a closed system is zero (Sigma F_ext = 0).", ["physics_mechanics.pdf"], ["momentum", "conserved", "external force"]),
        ("PHYS-008", "What is the difference between elastic and inelastic collisions?", "Elastic collisions conserve both kinetic energy and momentum; inelastic collisions conserve momentum but lose kinetic energy.", ["physics_mechanics.pdf"], ["elastic", "inelastic", "kinetic energy"]),
        ("PHYS-009", "What is the formula for centripetal acceleration?", "Centripetal acceleration is a_c = v^2 / r, directed radially inward toward the center.", ["physics_mechanics.pdf"], ["centripetal acceleration", "v^2 / r", "radially inward"]),
        ("PHYS-010", "How is angular momentum defined for a rigid body?", "L = I * omega, where I is moment of inertia and omega is angular velocity.", ["physics_mechanics.pdf"], ["angular momentum", "moment of inertia", "I * omega"]),
        ("PHYS-011", "What is the relationship between torque and angular momentum?", "Torque is the time rate of change of angular momentum: tau = dL/dt.", ["physics_mechanics.pdf"], ["torque", "dL/dt", "angular momentum"]),
        ("PHYS-012", "What is the formula for the period of a mass-spring harmonic oscillator?", "T = 2*pi*sqrt(m/k), where m is mass and k is spring constant.", ["physics_mechanics.pdf"], ["period", "2*pi*sqrt(m/k)", "harmonic oscillator"]),
    ]
    for qid, q, a, src, kw in physics_mech:
        questions.append(GoldenQAPair(qid, "Physics - Mechanics", q, a, src, kw, True))

    # 2. Physics - Thermodynamics (11 questions)
    physics_thermo = [
        ("THERMO-001", "What does the zeroth law of thermodynamics establish?", "Thermal equilibrium and temperature as a fundamental state variable.", ["physics_thermodynamics.pdf"], ["zeroth law", "thermal equilibrium", "temperature"]),
        ("THERMO-002", "State the first law of thermodynamics equation.", "Delta U = Q - W, where Delta U is change in internal energy, Q is heat added, and W is work done.", ["physics_thermodynamics.pdf"], ["first law", "Delta U = Q - W", "internal energy"]),
        ("THERMO-003", "What is the ideal gas law equation?", "PV = nRT, where P is pressure, V is volume, n is moles, R is gas constant, and T is temperature.", ["physics_thermodynamics.pdf"], ["ideal gas", "PV = nRT", "temperature"]),
        ("THERMO-004", "What occurs during an isothermal process in an ideal gas?", "Temperature remains constant, Delta U = 0, and Q = W = nRT * ln(V_f / V_i).", ["physics_thermodynamics.pdf"], ["isothermal", "Delta U = 0", "constant temperature"]),
        ("THERMO-005", "What defines an adiabatic process?", "No heat is exchanged (Q = 0) between system and surroundings, with P * V^gamma = constant.", ["physics_thermodynamics.pdf"], ["adiabatic", "Q = 0", "P * V^gamma"]),
        ("THERMO-006", "What is the heat capacity ratio gamma?", "gamma = C_p / C_v, the ratio of molar heat capacity at constant pressure to constant volume.", ["physics_thermodynamics.pdf"], ["gamma", "C_p / C_v", "heat capacity ratio"]),
        ("THERMO-007", "What does the second law of thermodynamics state about entropy?", "Total entropy of an isolated system always increases in any spontaneous natural process (Delta S >= 0).", ["physics_thermodynamics.pdf"], ["second law", "entropy", "Delta S >= 0", "isolated system"]),
        ("THERMO-008", "What is the maximum theoretical efficiency of a Carnot heat engine?", "eta_carnot = 1 - (T_c / T_h), where T_h is hot reservoir temperature and T_c is cold reservoir temperature.", ["physics_thermodynamics.pdf"], ["Carnot", "efficiency", "1 - (T_c / T_h)"]),
        ("THERMO-009", "What does the third law of thermodynamics state?", "The entropy of a pure crystalline substance approaches zero as temperature approaches absolute zero (0 Kelvin).", ["physics_thermodynamics.pdf"], ["third law", "entropy", "absolute zero", "0 Kelvin"]),
        ("THERMO-010", "Can a heat engine operate with 100% efficiency?", "No, the second law and Carnot limit dictate efficiency cannot reach 100% since T_c > 0.", ["physics_thermodynamics.pdf"], ["efficiency", "Carnot", "second law"]),
        ("THERMO-011", "How is work calculated for an isothermal expansion of an ideal gas?", "W = nRT * ln(V_f / V_i).", ["physics_thermodynamics.pdf"], ["isothermal", "W = nRT * ln", "expansion"]),
    ]
    for qid, q, a, src, kw in physics_thermo:
        questions.append(GoldenQAPair(qid, "Physics - Thermodynamics", q, a, src, kw, True))

    # 3. Biology - Genetics & Molecular Biology (11 questions)
    bio_genetics = [
        ("GEN-001", "What are the nucleotide components of DNA?", "Deoxyribose sugar, a phosphate group, and one of four nitrogenous bases: adenine, thymine, guanine, cytosine.", ["biology_genetics.pdf"], ["nucleotide", "deoxyribose", "phosphate", "nitrogenous bases"]),
        ("GEN-002", "What are Chargaff's rules of base pairing?", "Adenine pairs with thymine via two hydrogen bonds (A=T); guanine pairs with cytosine via three hydrogen bonds (G=C).", ["biology_genetics.pdf"], ["Chargaff", "base pairing", "hydrogen bonds", "A=T", "G=C"]),
        ("GEN-003", "Why is DNA replication called semiconservative?", "Each newly synthesized DNA molecule contains one original parental strand and one newly formed strand.", ["biology_genetics.pdf"], ["semiconservative", "parental strand", "replication"]),
        ("GEN-004", "In what direction does DNA polymerase synthesize DNA?", "In the 5' to 3' direction.", ["biology_genetics.pdf"], ["5' to 3'", "DNA polymerase", "direction"]),
        ("GEN-005", "What is the central dogma of molecular biology?", "Genetic information flows from DNA to RNA via transcription, and from RNA to protein via translation.", ["biology_genetics.pdf"], ["central dogma", "transcription", "translation", "DNA", "RNA"]),
        ("GEN-006", "What enzyme is responsible for synthesizing mRNA during transcription?", "RNA polymerase.", ["biology_genetics.pdf"], ["RNA polymerase", "transcription", "mRNA"]),
        ("GEN-007", "What is the role of tRNA in translation?", "tRNA transports specific amino acids to the ribosome, matching mRNA codons with complementary anticodons.", ["biology_genetics.pdf"], ["tRNA", "translation", "anticodon", "amino acids"]),
        ("GEN-008", "What amino acid does the start codon AUG code for?", "Methionine.", ["biology_genetics.pdf"], ["AUG", "start codon", "methionine"]),
        ("GEN-009", "State Mendel's law of segregation.", "Alleles separate during gamete formation so each gamete carries only one allele for each gene.", ["biology_genetics.pdf"], ["law of segregation", "alleles", "gamete"]),
        ("GEN-010", "State Mendel's law of independent assortment.", "Alleles of different genes segregate independently of one another during gamete formation.", ["biology_genetics.pdf"], ["independent assortment", "segregate independently", "genes"]),
        ("GEN-011", "What is a frameshift mutation?", "A genetic mutation caused by indels (insertions or deletions) of nucleotides not divisible by three, shifting the reading frame.", ["biology_genetics.pdf"], ["frameshift", "insertions", "deletions", "reading frame"]),
    ]
    for qid, q, a, src, kw in bio_genetics:
        questions.append(GoldenQAPair(qid, "Biology - Genetics", q, a, src, kw, True))

    # 4. Biology - Cell Biology (11 questions)
    bio_cell = [
        ("CELL-001", "What is the fundamental difference between prokaryotic and eukaryotic cells?", "Prokaryotes lack membrane-bound organelles and a true nucleus; eukaryotes have compartmentalized organelles and a nucleus.", ["biology_cell_biology.pdf"], ["prokaryotic", "eukaryotic", "nucleus", "membrane-bound"]),
        ("CELL-002", "Describe the fluid mosaic model of the plasma membrane.", "An amphipathic phospholipid bilayer with embedded integral and peripheral proteins, cholesterol, and carbohydrates.", ["biology_cell_biology.pdf"], ["fluid mosaic", "phospholipid bilayer", "amphipathic"]),
        ("CELL-003", "What is the primary function of mitochondria?", "Generating ATP through cellular respiration including glycolysis, Krebs cycle, and oxidative phosphorylation.", ["biology_cell_biology.pdf"], ["mitochondria", "ATP", "cellular respiration", "oxidative phosphorylation"]),
        ("CELL-004", "What does the endosymbiotic theory explain?", "The evolutionary origin of mitochondria and chloroplasts as engulfed prokaryotes inside ancestral eukaryotic cells.", ["biology_cell_biology.pdf"], ["endosymbiotic theory", "mitochondria", "chloroplasts", "prokaryotes"]),
        ("CELL-005", "What is the structural difference between rough and smooth endoplasmic reticulum?", "Rough ER is studded with ribosomes for protein synthesis; smooth ER lacks ribosomes and synthesizes lipids and metabolizes carbs.", ["biology_cell_biology.pdf"], ["rough ER", "smooth ER", "ribosomes", "lipids"]),
        ("CELL-006", "What is the role of the Golgi apparatus?", "Modifying, sorting, and packaging proteins from the rough ER for secretion or intracellular transport.", ["biology_cell_biology.pdf"], ["Golgi apparatus", "modifying", "sorting", "packaging"]),
        ("CELL-007", "What are lysosomes and what is their internal pH?", "Digestive organelles containing acid hydrolases for waste degradation with an optimal acidic pH of ~4.5-5.0.", ["biology_cell_biology.pdf"], ["lysosomes", "acid hydrolases", "pH 4.5", "degradation"]),
        ("CELL-008", "What cellular process generates ATP in the presence of oxygen?", "Cellular respiration (oxidative phosphorylation in mitochondria).", ["biology_cell_biology.pdf"], ["ATP", "respiration", "mitochondria"]),
        ("CELL-009", "Where are secretory proteins synthesized in eukaryotic cells?", "On the ribosomes attached to the rough endoplasmic reticulum.", ["biology_cell_biology.pdf"], ["rough endoplasmic reticulum", "ribosomes", "secretory"]),
        ("CELL-010", "What organelle stores calcium ions and synthesizes lipids?", "Smooth endoplasmic reticulum.", ["biology_cell_biology.pdf"], ["smooth ER", "calcium", "lipid synthesis"]),
        ("CELL-011", "How do cells digest their own damaged organelles?", "Through autophagy mediated by lysosomes containing acid hydrolases.", ["biology_cell_biology.pdf"], ["autophagy", "lysosomes", "acid hydrolases"]),
    ]
    for qid, q, a, src, kw in bio_cell:
        questions.append(GoldenQAPair(qid, "Biology - Cell Biology", q, a, src, kw, True))

    # 5. Computer Science - Algorithms (11 questions)
    cs_algo = [
        ("CS-001", "What does Big-O notation represent in algorithm analysis?", "The asymptotic upper bound of time or space complexity as input size n approaches infinity.", ["cs_algorithms.pdf"], ["Big-O", "asymptotic", "upper bound", "complexity"]),
        ("CS-002", "What is the average and worst-case time complexity of Quicksort?", "Average-case is O(n log n); worst-case is O(n^2) when poor pivots are chosen.", ["cs_algorithms.pdf"], ["Quicksort", "O(n log n)", "O(n^2)", "pivot"]),
        ("CS-003", "What is the time complexity and stability of Mergesort?", "Guaranteed O(n log n) in all cases, stable, requiring O(n) auxiliary space.", ["cs_algorithms.pdf"], ["Mergesort", "O(n log n)", "stable", "auxiliary space"]),
        ("CS-004", "What is the time complexity of Binary Search?", "O(log n) on sorted arrays by repeatedly halving the search space.", ["cs_algorithms.pdf"], ["Binary search", "O(log n)", "sorted array"]),
        ("CS-005", "What is the time complexity of Dijkstra's algorithm with a priority queue?", "O((V + E) log V), where V is vertices and E is edges.", ["cs_algorithms.pdf"], ["Dijkstra", "O((V + E) log V)", "priority queue"]),
        ("CS-006", "Can Dijkstra's algorithm handle negative edge weights?", "No, Dijkstra requires non-negative edge weights; negative weights require Bellman-Ford.", ["cs_algorithms.pdf"], ["Dijkstra", "non-negative", "negative edge"]),
        ("CS-007", "What are the two key properties required for dynamic programming?", "Overlapping subproblems and optimal substructure.", ["cs_algorithms.pdf"], ["dynamic programming", "overlapping subproblems", "optimal substructure"]),
        ("CS-008", "What is the average-case time complexity of hash table operations?", "O(1) constant time for search, insertion, and deletion.", ["cs_algorithms.pdf"], ["hash table", "O(1)", "average-case"]),
        ("CS-009", "How do hash tables resolve collisions?", "Separate chaining (linked lists) or open addressing (linear probing, quadratic probing).", ["cs_algorithms.pdf"], ["hash tables", "collisions", "chaining", "open addressing"]),
        ("CS-010", "What algorithmic paradigm does Mergesort use?", "Divide and conquer.", ["cs_algorithms.pdf"], ["divide-and-conquer", "Mergesort"]),
        ("CS-011", "Why is Quicksort's worst-case O(n^2)?", "When the pivot is consistently the smallest or largest element, creating severely unbalanced partitions.", ["cs_algorithms.pdf"], ["Quicksort", "worst-case", "unbalanced pivot"]),
    ]
    for qid, q, a, src, kw in cs_algo:
        questions.append(GoldenQAPair(qid, "Computer Science - Algorithms", q, a, src, kw, True))

    # 6. Computer Science - Operating Systems (11 questions)
    cs_os = [
        ("OS-001", "What is the difference between a process and a thread?", "A process is an isolated program in execution with its own memory; a thread is a lightweight execution unit sharing memory with peer threads.", ["cs_operating_systems.pdf"], ["process", "thread", "memory", "lightweight"]),
        ("OS-002", "What are Coffman's four conditions for deadlock?", "Mutual exclusion, hold and wait, no preemption, and circular wait.", ["cs_operating_systems.pdf"], ["deadlock", "mutual exclusion", "hold and wait", "no preemption", "circular wait"]),
        ("OS-003", "What is the role of the Translation Lookaside Buffer (TLB)?", "A fast hardware cache that stores recent virtual-to-physical address translations to speed up paging.", ["cs_operating_systems.pdf"], ["TLB", "Translation Lookaside Buffer", "cache", "paging"]),
        ("OS-004", "What is Belady's anomaly in page replacement?", "A phenomenon where increasing page frames leads to an increase in page faults in FIFO replacement.", ["cs_operating_systems.pdf"], ["Belady's anomaly", "FIFO", "page faults", "page frames"]),
        ("OS-005", "What is virtual memory?", "A memory management technique that maps virtual addresses to physical frames using paging to give processes the illusion of large contiguous memory.", ["cs_operating_systems.pdf"], ["virtual memory", "paging", "physical frames", "page tables"]),
        ("OS-006", "What is Round Robin CPU scheduling?", "A preemptive scheduling algorithm that assigns each process a fixed time slice (quantum) in cyclic order.", ["cs_operating_systems.pdf"], ["Round Robin", "quantum", "CPU scheduling", "preemptive"]),
        ("OS-007", "What is the optimal page replacement algorithm (OPT)?", "Replaces the page that will not be used for the longest period of time in the future.", ["cs_operating_systems.pdf"], ["optimal", "OPT", "page replacement", "longest period"]),
        ("OS-008", "What is LRU page replacement?", "Least Recently Used: replaces the page that has not been accessed for the longest time.", ["cs_operating_systems.pdf"], ["LRU", "Least Recently Used", "page replacement"]),
        ("OS-009", "How can deadlock be prevented?", "By invalidating at least one of Coffman's four conditions (e.g. eliminating circular wait by ordering resources).", ["cs_operating_systems.pdf"], ["deadlock", "prevention", "circular wait", "Coffman"]),
        ("OS-010", "What components comprise a process context?", "Program counter, registers, CPU stack, heap, and data section.", ["cs_operating_systems.pdf"], ["process", "program counter", "stack", "registers"]),
        ("OS-011", "What is the purpose of an operating system?", "Managing computer hardware resources and providing a common platform for application execution.", ["cs_operating_systems.pdf"], ["operating system", "hardware", "resources", "applications"]),
    ]
    for qid, q, a, src, kw in cs_os:
        questions.append(GoldenQAPair(qid, "Computer Science - Operating Systems", q, a, src, kw, True))

    # 7. Mathematics - Linear Algebra (10 questions)
    math_la = [
        ("MATH-LA-001", "What is the Rank-Nullity Theorem for an m x n matrix A?", "rank(A) + nullity(A) = n, where n is the number of columns.", ["math_linear_algebra.pdf"], ["Rank-Nullity Theorem", "rank(A) + nullity(A) = n", "columns"]),
        ("MATH-LA-002", "What is an eigenvalue and eigenvector of a matrix A?", "Av = lambda * v with non-zero vector v, where lambda is the scalar eigenvalue and v is the eigenvector.", ["math_linear_algebra.pdf"], ["eigenvalue", "eigenvector", "Av = lambda * v"]),
        ("MATH-LA-003", "How are eigenvalues calculated?", "By finding the roots of the characteristic equation det(A - lambda * I) = 0.", ["math_linear_algebra.pdf"], ["characteristic polynomial", "det(A - lambda * I) = 0", "eigenvalues"]),
        ("MATH-LA-004", "When is a square matrix diagonalizable?", "When it has n linearly independent eigenvectors.", ["math_linear_algebra.pdf"], ["diagonalizable", "linearly independent eigenvectors"]),
        ("MATH-LA-005", "What is the spectral theorem for real symmetric matrices?", "Real symmetric matrices are orthogonally diagonalizable: A = Q * Lambda * Q^T.", ["math_linear_algebra.pdf"], ["symmetric matrices", "orthogonally diagonalizable", "Q * Lambda * Q^T"]),
        ("MATH-LA-006", "What is Singular Value Decomposition (SVD)?", "A factorization A = U * Sigma * V^T, where U and V are orthogonal matrices and Sigma contains non-negative singular values.", ["math_linear_algebra.pdf"], ["Singular Value Decomposition", "SVD", "U * Sigma * V^T", "singular values"]),
        ("MATH-LA-007", "What defines linear independence for a set of vectors?", "The only linear combination equaling the zero vector is when all scalar coefficients are zero.", ["math_linear_algebra.pdf"], ["linear independence", "coefficients equal to zero", "vectors"]),
        ("MATH-LA-008", "What is the rank of a matrix?", "The maximum number of linearly independent row or column vectors.", ["math_linear_algebra.pdf"], ["rank", "linearly independent", "dimension"]),
        ("MATH-LA-009", "What is a vector space?", "A set closed under vector addition and scalar multiplication satisfying associative and distributive axioms.", ["math_linear_algebra.pdf"], ["vector space", "closed", "scalar multiplication"]),
        ("MATH-LA-010", "What are singular values in SVD?", "The square roots of the eigenvalues of A^T * A.", ["math_linear_algebra.pdf"], ["singular values", "SVD", "eigenvalues"]),
    ]
    for qid, q, a, src, kw in math_la:
        questions.append(GoldenQAPair(qid, "Mathematics - Linear Algebra", q, a, src, kw, True))

    # 8. Mathematics - Calculus (8 questions)
    math_calc = [
        ("MATH-CALC-001", "What is the limit definition of the derivative f'(x)?", "f'(x) = lim(h->0) [f(x+h) - f(x)] / h.", ["math_calculus.pdf"], ["derivative", "limit", "[f(x+h) - f(x)] / h"]),
        ("MATH-CALC-002", "What is the Fundamental Theorem of Calculus?", "If F'(x) = f(x), then integral from a to b of f(x) dx = F(b) - F(a).", ["math_calculus.pdf"], ["Fundamental Theorem of Calculus", "F(b) - F(a)", "integral"]),
        ("MATH-CALC-003", "State the chain rule for derivatives.", "d/dx[f(g(x))] = f'(g(x)) * g'(x).", ["math_calculus.pdf"], ["chain rule", "f'(g(x)) * g'(x)"]),
        ("MATH-CALC-004", "What does Taylor's theorem state?", "Any smooth function can be approximated by a polynomial: f(x) = sum [f^(n)(a) / n!] * (x - a)^n.", ["math_calculus.pdf"], ["Taylor's theorem", "polynomial", "sum"]),
        ("MATH-CALC-005", "What are the three conditions for continuity at x = c?", "lim(x->c) f(x) exists, f(c) is defined, and lim(x->c) f(x) = f(c).", ["math_calculus.pdf"], ["continuous", "limit exists", "f(c) is defined"]),
        ("MATH-CALC-006", "State the Mean Value Theorem.", "For f continuous on [a,b] and differentiable on (a,b), there exists c in (a,b) where f'(c) = [f(b) - f(a)] / (b - a).", ["math_calculus.pdf"], ["Mean Value Theorem", "f'(c) = [f(b) - f(a)] / (b - a)"]),
        ("MATH-CALC-007", "What does the derivative geometrically represent?", "The slope of the tangent line to the function graph at that point.", ["math_calculus.pdf"], ["derivative", "slope", "tangent line"]),
        ("MATH-CALC-008", "What is the derivative of e^x?", "e^x.", ["math_calculus.pdf"], ["derivative", "e^x"]),
    ]
    for qid, q, a, src, kw in math_calc:
        questions.append(GoldenQAPair(qid, "Mathematics - Calculus", q, a, src, kw, True))

    # 9. Unanswerable / Out-of-Domain Questions (20 questions)
    # These test whether the RAG pipeline correctly REFUSES to answer or admits no information,
    # rather than hallucinating plausible-sounding falsehoods!
    unanswerable_questions = [
        ("UNANS-001", "What is the string landscape in M-theory compactifications?", "This topic is not covered in the provided study materials.", [], ["string landscape", "M-theory"]),
        ("UNANS-002", "How do you cook authentic beef Wellington?", "This topic is not covered in the provided study materials.", [], ["beef wellington", "cook"]),
        ("UNANS-003", "Who won the FIFA World Cup in 1994?", "This topic is not covered in the provided study materials.", [], ["World Cup", "1994"]),
        ("UNANS-004", "What were the primary economic causes of the Peloponnesian War?", "This topic is not covered in the provided study materials.", [], ["Peloponnesian War"]),
        ("UNANS-005", "Explain the Byzantine Paxos consensus algorithm in distributed systems.", "This topic is not covered in the provided study materials.", [], ["Byzantine Paxos"]),
        ("UNANS-006", "What is the plot summary of War and Peace by Leo Tolstoy?", "This topic is not covered in the provided study materials.", [], ["War and Peace", "Tolstoy"]),
        ("UNANS-007", "How does quantum chromodynamics model asymptotic freedom of quarks?", "This topic is not covered in the provided study materials.", [], ["quantum chromodynamics", "asymptotic freedom"]),
        ("UNANS-008", "What is the capital of Madagascar?", "This topic is not covered in the provided study materials.", [], ["Madagascar", "capital"]),
        ("UNANS-009", "How do you calibrate an HPLC chromatography column for organic synthesis?", "This topic is not covered in the provided study materials.", [], ["HPLC", "chromatography"]),
        ("UNANS-010", "What are the rules of Texas Hold'em poker?", "This topic is not covered in the provided study materials.", [], ["poker", "Texas Hold'em"]),
        ("UNANS-011", "What happened during the Meiji Restoration in Japan?", "This topic is not covered in the provided study materials.", [], ["Meiji Restoration"]),
        ("UNANS-012", "How does CRISPR-Cas9 guide RNA design differ from Cas12a?", "This topic is not covered in the provided study materials.", [], ["Cas12a", "CRISPR"]),
        ("UNANS-013", "What is the recipe for chocolate lava cake?", "This topic is not covered in the provided study materials.", [], ["lava cake", "recipe"]),
        ("UNANS-014", "Explain the Riemann Hypothesis and non-trivial zeros.", "This topic is not covered in the provided study materials.", [], ["Riemann Hypothesis", "zeros"]),
        ("UNANS-015", "Who composed the Four Seasons violin concertos?", "This topic is not covered in the provided study materials.", [], ["Four Seasons", "violin"]),
        ("UNANS-016", "What is the legal doctrine of promissory estoppel in contract law?", "This topic is not covered in the provided study materials.", [], ["promissory estoppel", "contract law"]),
        ("UNANS-017", "What are the stages of sleep and REM cycles in neuroscience?", "This topic is not covered in the provided study materials.", [], ["REM cycles", "sleep"]),
        ("UNANS-018", "How do black hole information paradox and Hawking radiation resolve?", "This topic is not covered in the provided study materials.", [], ["Hawking radiation", "information paradox"]),
        ("UNANS-019", "What is the syntax for defining an async generator in Rust?", "This topic is not covered in the provided study materials.", [], ["async generator", "Rust"]),
        ("UNANS-020", "Who was the first emperor of the Qin dynasty in China?", "This topic is not covered in the provided study materials.", [], ["Qin dynasty", "emperor"]),
    ]
    for qid, q, a, src, kw in unanswerable_questions:
        questions.append(GoldenQAPair(qid, "Unanswerable / Out-of-Domain", q, a, src, kw, False))

    return questions


def save_dataset_json(output_path: str = "./data/golden_benchmark.json"):
    questions = build_golden_dataset()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": "1.0",
        "total_questions": len(questions),
        "answerable_count": sum(1 for q in questions if q.is_answerable),
        "unanswerable_count": sum(1 for q in questions if not q.is_answerable),
        "questions": [q.to_dict() for q in questions],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return payload


if __name__ == "__main__":
    data = save_dataset_json()
    print(f"Generated Golden Benchmark Dataset: {data['total_questions']} questions")
    print(f"- Answerable: {data['answerable_count']}")
    print(f"- Unanswerable (Anti-Hallucination): {data['unanswerable_count']}")
