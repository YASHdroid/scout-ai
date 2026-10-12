"use client";

import { useEffect, useRef, useState } from "react";
import {
  motion,
  useAnimationFrame,
  useMotionValue,
  useReducedMotion,
  useTransform,
  type MotionValue,
} from "motion/react";
import {
  ArrowDown,
  ArrowUpRight,
  Orbit,
  Search,
  FileText,
  Compass,
  BrainCircuit,
  Network,
  ShieldCheck,
} from "lucide-react";
import SignalField from "../components/SignalField";

const features = [
  {
    number: "01",
    label: "DISCOVER",
    title: "Find what matters",
    description:
      "Explore relevant sources instead of getting lost in endless search results.",
    icon: Search,
  },
  {
    number: "02",
    label: "CONNECT",
    title: "See the bigger picture",
    description:
      "Bring findings together to understand patterns, comparisons, and perspectives.",
    icon: Orbit,
  },
  {
    number: "03",
    label: "UNDERSTAND",
    title: "Leave with clarity",
    description:
      "Turn research into structured findings with sources you can investigate further.",
    icon: FileText,
  },
];

const researchStages = [
  {
    number: "01",
    category: "PLANNING",
    code: "STG-0142",
    title: "Start with the right questions",
    description: "Break a complex question into focused research topics.",
    detail: "QUESTIONS & SUBTOPICS",
    icon: Compass,
  },
  {
    number: "02",
    category: "DISCOVERY",
    code: "STG-0317",
    title: "Explore relevant sources",
    description: "Discover webpages and gather information from multiple sources.",
    detail: "WEB PAGES & REFERENCES",
    icon: Search,
  },
  {
    number: "03",
    category: "ANALYSIS",
    code: "STG-0409",
    title: "Understand the evidence",
    description: "Examine findings, compare perspectives, and identify useful evidence.",
    detail: "SOURCE CONTENT & FINDINGS",
    icon: BrainCircuit,
  },
  {
    number: "04",
    category: "SYNTHESIS",
    code: "STG-0521",
    title: "Connect the bigger picture",
    description: "Bring findings together into a structured research report.",
    detail: "COMPARISONS & KEY INSIGHTS",
    icon: Network,
  },
  {
    number: "05",
    category: "VERIFICATION",
    code: "STG-0633",
    title: "Check before presenting",
    description: "Evaluate report claims against available source evidence.",
    detail: "CLAIMS & SOURCE EVIDENCE",
    icon: ShieldCheck,
  },
];

const goals = [
  {
    number: "01",
    title: "Explore the unfamiliar",
    description:
      "Understand emerging technologies, unfamiliar concepts, and ideas beyond your current knowledge.",
    tag: "LEARN",
  },
  {
    number: "02",
    title: "Compare what matters",
    description:
      "Investigate different approaches, evaluate available evidence, and understand the trade-offs.",
    tag: "COMPARE",
  },
  {
    number: "03",
    title: "Build a clearer picture",
    description:
      "Connect findings from different sources and turn scattered information into useful understanding.",
    tag: "DISCOVER",
  },
];

type ResearchStage = (typeof researchStages)[number];

type OrbitCardProps = {
  stage: ResearchStage;
  index: number;
  rotation: MotionValue<number>;
  radiusX: number;
  radiusY: number;
  selected: boolean;
  reduceMotion: boolean;
  onSelect: (number: string) => void;
};

/** Hairline on top of an open column: faint full-width rule, cyan segment grows on hover. */
function ColumnRule() {
  return (
    <>
      <span
        aria-hidden="true"
        className="absolute left-0 top-0 h-px w-full bg-gradient-to-r from-white/20 to-transparent"
      />
      <span
        aria-hidden="true"
        className="absolute left-0 top-0 h-px w-10 bg-cyan-300 transition-all duration-500 group-hover:w-full"
      />
    </>
  );
}

function OrbitCard({
  stage,
  index,
  rotation,
  radiusX,
  radiusY,
  selected,
  reduceMotion,
  onSelect,
}: OrbitCardProps) {
  const angleAt = (degrees: number) =>
    ((degrees + index * (360 / researchStages.length) - 90) * Math.PI) / 180;

  // Each card follows its own elliptical position.
  const x = useTransform(
    rotation,
    (degrees) => Math.cos(angleAt(degrees)) * radiusX - 102
  );

  const y = useTransform(
    rotation,
    (degrees) => Math.sin(angleAt(degrees)) * radiusY - 140
  );

  // Front cards are larger and brighter than cards at the back.
  const depth = useTransform(
    rotation,
    (degrees) => (Math.sin(angleAt(degrees)) + 1) / 2
  );

  const scale = useTransform(depth, (value) => 0.78 + value * 0.22);
  const opacity = useTransform(depth, (value) => 0.42 + value * 0.58);
  const zIndex = useTransform(depth, (value) => Math.round(value * 100));

  const Icon = stage.icon;

  return (
    <motion.button
      type="button"
      aria-label={`Select ${stage.title} and accelerate the orbit`}
      aria-pressed={selected}
      onClick={() => onSelect(stage.number)}
      style={{ x, y, scale, opacity, zIndex }}
      className={`absolute left-1/2 top-1/2 flex w-[156px] flex-col overflow-hidden rounded-xl border p-3 text-left shadow-2xl backdrop-blur-md transition-colors duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 sm:w-[190px] sm:p-4 lg:w-[204px] ${
        selected
          ? "border-cyan-300/80 bg-[#0D1B29] shadow-[0_0_35px_rgba(34,211,238,0.16)]"
          : "border-white/15 bg-[#0A1019]/95 hover:border-cyan-300/50"
      }`}
    >
      <span className="mb-2 flex items-center justify-between gap-1">
        <span className="truncate text-[8px] font-semibold tracking-[0.13em] text-cyan-300 sm:text-[10px]">
          {stage.category}
        </span>

        <span className="shrink-0 font-mono text-[8px] text-white/30 sm:text-[9px]">
          {stage.code}
        </span>
      </span>

      {/* Card signal visualization */}
      <div
        aria-hidden="true"
        className="relative mb-3 h-[50px] overflow-hidden rounded-md border border-white/10 sm:h-[68px] lg:h-[76px]"
        style={{
          backgroundImage:
            "radial-gradient(circle, rgba(160,180,200,0.60) 1px, transparent 1.5px), radial-gradient(ellipse at 28% 50%, rgba(0,180,255,0.4), transparent 58%)",
          backgroundSize: "8px 8px, 100% 100%",
        }}
      >
        <motion.div
          className="absolute inset-y-0 left-0 w-1/2 bg-gradient-to-r from-transparent via-cyan-400/20 to-transparent blur-md"
          animate={reduceMotion ? undefined : { x: ["-100%", "220%"] }}
          transition={{
            duration: 4 + index,
            repeat: reduceMotion ? 0 : Infinity,
            ease: "linear",
          }}
        />
      </div>

      <p className="mb-1 text-[8px] tracking-[0.12em] text-white/35 sm:text-[9px]">
        STAGE {stage.number}
      </p>

      <h3 className="line-clamp-2 text-sm font-medium leading-5 tracking-tight text-white sm:text-base sm:leading-6">
        {stage.title}
      </h3>

      <p className="mt-1 line-clamp-3 text-[9px] leading-4 text-white/50 sm:mt-2 sm:text-[11px] sm:leading-[18px]">
        {stage.description}
      </p>

      <div className="mt-auto hidden border-t border-white/10 pt-2 sm:block">
        <p className="text-[8px] leading-4 tracking-[0.08em] text-white/40">
          BUILT FROM
        </p>
        <p className="mt-0.5 truncate text-[9px] leading-4 text-white/65">
          {stage.detail}
        </p>
      </div>

      <Icon className="absolute bottom-3 right-3 h-3.5 w-3.5 text-cyan-300/60 sm:hidden" />
    </motion.button>
  );
}

export default function Home() {
  // useReducedMotion() can return null; normalise so it fits `boolean` props.
  const reduceMotion = useReducedMotion() ?? false;

  const rotation = useMotionValue(0);

  const [fastOrbit, setFastOrbit] = useState(false);
  const [activeCard, setActiveCard] = useState<string | null>(null);
  const [viewportWidth, setViewportWidth] = useState(1280);

  const speedTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const updateWidth = () => setViewportWidth(window.innerWidth);

    updateWidth();
    window.addEventListener("resize", updateWidth);

    return () => window.removeEventListener("resize", updateWidth);
  }, []);

  useEffect(() => {
    return () => {
      if (speedTimeout.current) clearTimeout(speedTimeout.current);
    };
  }, []);

  useAnimationFrame((_time, delta) => {
    if (reduceMotion) return;

    const speed = fastOrbit ? 0.09 : 0.012;
    rotation.set((rotation.get() + delta * speed) % 360);
  });

  const radiusX =
    viewportWidth < 640
      ? viewportWidth * 0.22
      : viewportWidth < 1024
        ? viewportWidth * 0.29
        : Math.min(410, viewportWidth * 0.34);

  const radiusY =
    viewportWidth < 640 ? 112 : viewportWidth < 1024 ? 170 : 220;

  function handleCardClick(number: string) {
    setActiveCard(number);
    setFastOrbit(true);

    if (speedTimeout.current) clearTimeout(speedTimeout.current);

    speedTimeout.current = setTimeout(() => {
      setFastOrbit(false);
    }, 3000);
  }

  function resetOrbit() {
    setFastOrbit(false);
    setActiveCard(null);

    if (speedTimeout.current) {
      clearTimeout(speedTimeout.current);
      speedTimeout.current = null;
    }
  }

  return (
    <>
      {/* One dot field behind the whole page: no per-section backgrounds, no seams */}
      <SignalField />

      <main className="relative z-10 min-h-screen overflow-x-clip text-[#F4F7FB]">
        {/* Navigation */}
        <header className="relative z-20 mx-auto flex max-w-7xl items-center justify-between px-6 py-6 md:px-10">
          <a href="#home" className="flex items-center gap-2.5">
            <Orbit className="h-7 w-7 text-cyan-300" strokeWidth={1.6} />
            <span className="font-[family-name:var(--font-scout-wordmark)] text-2xl font-bold tracking-[-0.075em]">
  S C O U T<span className="text-cyan-300"></span>
</span>
          </a>

          <nav className="hidden items-center gap-8 text-sm text-white/60 md:flex">
            <a href="#why-scout" className="transition hover:text-white">
              Why Scout
            </a>
            <a href="#how-it-works" className="transition hover:text-white">
              How it works
            </a>
            <a href="#research-goals" className="transition hover:text-white">
              What you can do
            </a>
          </nav>

          <a
          href="/login"
            className="group flex items-center gap-2 rounded-full border border-white/15 px-4 py-2.5 text-sm transition hover:border-cyan-300/60 hover:bg-cyan-300/5"
          >
            Try it free
            <ArrowUpRight
              size={15}
              className="transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
            />
          </a>
        </header>

        {/* Hero */}
        <section
          id="home"
          className="relative z-10 mx-auto flex min-h-[calc(100svh-85px)] max-w-7xl flex-col items-center justify-center px-6 pb-20 pt-12 text-center md:px-10"
        >
          <motion.div
            initial={reduceMotion ? false : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7 }}
            className="mb-9 flex items-center gap-2 rounded-full border border-cyan-200/15 bg-cyan-200/[0.04] px-3.5 py-2 text-[10px] font-medium tracking-[0.2em] text-cyan-100/80 sm:text-xs"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-300 shadow-[0_0_12px_#67e8f9]" />
            A RESEARCH ENGINE FOR THE CURIOUS
          </motion.div>

          <motion.h1
            initial={reduceMotion ? false : { opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, delay: 0.1 }}
            className="max-w-5xl text-5xl font-medium leading-[1.08] tracking-[-0.065em] sm:text-7xl lg:text-[100px]"
          >
           The answer is only
            <br />
            <span className="font-serif font-normal italic text-cyan-300">
            the Beginning.
            </span>
          </motion.h1>

          <motion.p
  initial={reduceMotion ? false : { opacity: 0, y: 18 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.8, delay: 0.3 }}
  className="mt-7 max-w-xl text-base leading-7 text-white/70 sm:text-lg"
>
  Go beyond quick answers. Explore sources, connect ideas, and
  uncover the evidence behind what matters.
</motion.p>

          <motion.div
            initial={reduceMotion ? false : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.45 }}
            className="mt-9 flex flex-col items-center gap-4 sm:flex-row"
          >
            <a
              href="/login"
              className="group inline-flex items-center gap-3 rounded-full bg-cyan-300 px-6 py-3.5 text-sm font-semibold text-[#061019] transition hover:bg-cyan-200"
            >
              Start exploring
              <ArrowUpRight
                size={17}
                className="transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
              />
            </a>

            <a
              href="#how-it-works"
              className="inline-flex items-center gap-2 px-4 py-3 text-sm text-white/75 transition hover:text-white"
            >
              Discover how it works
              <ArrowDown size={15} />
            </a>
          </motion.div>

          <motion.div
            aria-hidden="true"
            initial={reduceMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8, duration: 1 }}
            className="mt-16 flex items-center gap-3 text-[10px] tracking-[0.24em] text-white/50 sm:mt-20"
          >
            <span className="h-px w-10 bg-gradient-to-r from-transparent to-cyan-300/50" />
            FROM CURIOSITY TO CLARITY
            <span className="h-px w-10 bg-gradient-to-l from-transparent to-cyan-300/50" />
          </motion.div>
        </section>

        {/* Why Scout */}
        <section id="why-scout" className="relative z-10 py-20 sm:py-28">
          <div className="mx-auto max-w-7xl px-6 md:px-10">
            <motion.div
              initial={reduceMotion ? false : { opacity: 0, y: 24 }}
              whileInView={reduceMotion ? undefined : { opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: 0.7 }}
              className="grid gap-8 md:grid-cols-[1.2fr_0.8fr] md:items-end"
            >
              <div>
                <p className="mb-5 text-xs tracking-[0.24em] text-cyan-300/80">
                  01 / WHY SCOUT
                </p>

                <h2 className="max-w-3xl text-4xl font-medium leading-tight tracking-[-0.05em] sm:text-6xl">
                  More than information.
                  <br />
                  <span className="font-serif font-normal italic text-cyan-300">
                    Real understanding.
                  </span>
                </h2>
              </div>

              <p className="max-w-lg text-base leading-7 text-white/70 md:justify-self-end">
                Finding information is easy. Understanding what matters,
                connecting ideas, and knowing where the evidence leads takes
                deeper research. That is where Scout comes in.
              </p>
            </motion.div>

            <div className="mt-16 grid gap-12 md:grid-cols-3 md:gap-10">
              {features.map((feature, index) => {
                const Icon = feature.icon;

                return (
                  <motion.div
                    key={feature.number}
                    initial={reduceMotion ? false : { opacity: 0, y: 20 }}
                    whileInView={reduceMotion ? undefined : { opacity: 1, y: 0 }}
                    viewport={{ once: true, amount: 0.2 }}
                    transition={{ duration: 0.6, delay: index * 0.12 }}
                    whileHover={reduceMotion ? undefined : { y: -5 }}
                    className="group relative pr-2 pt-8"
                  >
                    <ColumnRule />

                    <Icon className="mb-8 h-6 w-6 text-cyan-300" strokeWidth={1.5} />

                    <p className="mb-3 text-xs tracking-[0.18em] text-white/50">
                      {feature.number} — {feature.label}
                    </p>

                    <h3 className="text-xl font-medium tracking-tight">
                      {feature.title}
                    </h3>

                    <p className="mt-3 max-w-xs text-sm leading-6 text-white/65">
                      {feature.description}
                    </p>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </section>

        {/* How Scout Works */}
        <section id="how-it-works" className="relative z-10 py-20 sm:py-28">
          <div className="mx-auto max-w-7xl px-6 md:px-10">
            <motion.div
              initial={reduceMotion ? false : { opacity: 0, y: 24 }}
              whileInView={reduceMotion ? undefined : { opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: 0.7 }}
              className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between"
            >
              <div>
                <p className="mb-5 text-xs tracking-[0.24em] text-cyan-300/80">
                  02 / HOW IT WORKS
                </p>

                <h2 className="max-w-3xl text-4xl font-medium leading-tight tracking-[-0.05em] sm:text-6xl">
                  A question becomes
                  <br />
                  <span className="font-serif font-normal italic text-cyan-300">
                    an investigation.
                  </span>
                </h2>
              </div>

              <p className="max-w-md text-sm leading-7 text-white/70 md:pb-2">
                Five stages. Connected findings. One clearer picture. Explore
                the process as each stage moves through the orbit.
              </p>
            </motion.div>

            {/* Elliptical orbit: the page-wide dot field shows through behind it */}
            <div className="relative mx-auto mt-14 h-[580px] w-full max-w-6xl sm:h-[650px] lg:h-[740px]">
              <motion.div
                aria-hidden="true"
                className="pointer-events-none absolute left-1/2 top-1/2 h-40 w-40 -translate-x-1/2 -translate-y-1/2 rounded-full bg-cyan-400/10 blur-[65px]"
                animate={
                  reduceMotion
                    ? undefined
                    : { opacity: [0.4, 0.8, 0.4], scale: [0.9, 1.12, 0.9] }
                }
                transition={{
                  duration: 5,
                  repeat: reduceMotion ? 0 : Infinity,
                  ease: "easeInOut",
                }}
              />

              {researchStages.map((stage, index) => (
                <OrbitCard
                  key={stage.number}
                  stage={stage}
                  index={index}
                  rotation={rotation}
                  radiusX={radiusX}
                  radiusY={radiusY}
                  selected={activeCard === stage.number}
                  reduceMotion={reduceMotion}
                  onSelect={handleCardClick}
                />
              ))}

              {/* Central Scout identity */}
              <div className="pointer-events-none absolute left-1/2 top-1/2 z-[50] flex -translate-x-1/2 -translate-y-1/2 flex-col items-center">
                <div className="flex h-[68px] w-[68px] items-center justify-center rounded-full border border-cyan-300/30 bg-[#07111B] shadow-[0_0_50px_rgba(0,180,255,0.12)] sm:h-[82px] sm:w-[82px]">
                  <Orbit className="h-8 w-8 text-cyan-300 sm:h-10 sm:w-10" strokeWidth={1.4} />
                </div>

                <p className="mt-3 text-[10px] font-semibold tracking-[0.28em] text-white/75">
                  SCOUT
                </p>

                <p className="mt-1 text-[8px] tracking-[0.16em] text-cyan-300/65">
                  RESEARCH SYSTEM
                </p>
              </div>
            </div>

            {/* Orbit controls */}
            <div className="mx-auto mt-6 flex max-w-2xl flex-col items-center justify-center gap-4 text-center sm:flex-row sm:justify-between">
              <div className="flex items-center gap-3">
                <span
                  className={`h-2 w-2 rounded-full ${
                    fastOrbit
                      ? "bg-cyan-300 shadow-[0_0_12px_#67e8f9]"
                      : "bg-white/30"
                  }`}
                />

                <p className="text-[10px] tracking-[0.16em] text-white/60 sm:text-xs">
                  {fastOrbit
                    ? "ACCELERATING — FAST ORBIT"
                    : "CLICK ANY CARD TO ACCELERATE"}
                </p>
              </div>

              <button
                type="button"
                onClick={resetOrbit}
                className="text-xs text-cyan-300/80 transition hover:text-cyan-200"
              >
                Reset orbit ↺
              </button>
            </div>
          </div>
        </section>

        {/* Research goals */}
        <section id="research-goals" className="relative z-10 py-20 sm:py-28">
          <div className="mx-auto max-w-7xl px-6 md:px-10">
            <motion.div
              initial={reduceMotion ? false : { opacity: 0, y: 24 }}
              whileInView={reduceMotion ? undefined : { opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: 0.7 }}
            >
              <p className="mb-5 text-xs tracking-[0.24em] text-cyan-300/80">
                03 / WHERE CURIOSITY LEADS
              </p>

              <h2 className="max-w-4xl text-4xl font-medium leading-tight tracking-[-0.055em] sm:text-6xl">
                Don&apos;t just look for answers.
                <br />
                <span className="font-serif font-normal italic text-cyan-300">
                  Understand what they mean.
                </span>
              </h2>

              <p className="mt-6 max-w-xl text-base leading-7 text-white/70">
                Whether you&apos;re learning something new, evaluating an idea, or
                investigating a complex problem, start with a question worth
                exploring.
              </p>
            </motion.div>

            <div className="mt-16 grid gap-12 md:grid-cols-3 md:gap-10">
              {goals.map((item, index) => (
                <motion.div
                  key={item.number}
                  initial={reduceMotion ? false : { opacity: 0, y: 28 }}
                  whileInView={reduceMotion ? undefined : { opacity: 1, y: 0 }}
                  viewport={{ once: true, amount: 0.2 }}
                  transition={{ duration: 0.65, delay: index * 0.13 }}
                  whileHover={reduceMotion ? undefined : { y: -6 }}
                  className="group relative pr-2 pt-8"
                >
                  <ColumnRule />

                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-white/50">
                      {item.number}
                    </span>

                    <span className="rounded-full border border-white/10 px-3 py-1 font-mono text-[9px] tracking-[0.16em] text-cyan-300/80">
                      {item.tag}
                    </span>
                  </div>

                  <h3 className="mt-12 text-xl font-medium tracking-tight sm:text-2xl">
                    {item.title}
                  </h3>

                  <p className="mt-4 max-w-sm text-sm leading-6 text-white/65">
                    {item.description}
                  </p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Final call to action */}
        <section className="relative z-10 px-6 py-28 sm:py-40">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute left-1/2 top-1/2 h-[400px] w-[400px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-cyan-400/[0.07] blur-[120px]"
          />

          <motion.div
            initial={reduceMotion ? false : { opacity: 0, y: 25 }}
            whileInView={reduceMotion ? undefined : { opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.8 }}
            className="relative mx-auto flex max-w-4xl flex-col items-center text-center"
          >
            <div className="mb-7 flex items-center gap-2 text-[10px] tracking-[0.24em] text-cyan-300/80 sm:text-xs">
              <Orbit size={15} />
              YOUR NEXT DISCOVERY STARTS HERE
            </div>

            <h2 className="text-5xl font-medium leading-[1.08] tracking-[-0.065em] sm:text-7xl lg:text-8xl">
              Every discovery
              <br />
              starts with a{" "}
              <span className="font-serif font-normal italic text-cyan-300">
                question.
              </span>
            </h2>

            <p className="mt-7 max-w-lg text-base leading-7 text-white/70 sm:text-lg">
              Bring your curiosity. Scout will help you investigate your
              question, explore the evidence, and find a clearer direction.
            </p>

            <motion.a
           href="/login"
              whileHover={reduceMotion ? undefined : { y: -3 }}
              whileTap={reduceMotion ? undefined : { scale: 0.98 }}
              className="group mt-10 inline-flex items-center gap-3 rounded-full bg-cyan-300 px-7 py-4 text-sm font-semibold text-[#061019] transition-colors hover:bg-cyan-200"
            >
              Try searching for free
              <ArrowUpRight
                size={17}
                className="transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
              />
            </motion.a>

            <p className="mt-5 text-xs text-white/45">
              Start with a question. See where it leads.
            </p>
          </motion.div>
        </section>

        {/* Footer */}
        <footer className="relative z-10">
          <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-8 sm:flex-row sm:items-center sm:justify-between md:px-10">
            <a href="#home" className="flex items-center gap-2">
              <Orbit size={19} className="text-cyan-300" />
              <span className="font-semibold tracking-tight">
                S C O U T<span className="text-cyan-300"></span>
              </span>
            </a>

            <p className="text-xs text-white/50">
              Built for the curious. Designed for deeper research.
            </p>

            <a
              href="#home"
              className="text-xs text-white/60 transition hover:text-cyan-300"
            >
              Back to top ↑
            </a>
          </div>
        </footer>
      </main>
    </>
  );
}