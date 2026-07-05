import { motion } from "motion/react";
import { 
  Github, 
  Terminal, 
  Server, 
  Activity, 
  Cpu, 
  Zap, 
  Database, 
  Link as LinkIcon, 
  LayoutDashboard, 
  CreditCard,
  Gamepad2
} from "lucide-react";

const features = [
  {
    title: "Separation of Concerns",
    description: "Core game engine logic is cleanly separated from the Telegram interface and FSM layer.",
    icon: <Cpu className="w-6 h-6 text-neon-cyan" />
  },
  {
    title: "Atomic Transactions",
    description: "All transfers are atomic. If a transaction fails (e.g., due to insufficient funds), balances remain unchanged.",
    icon: <Zap className="w-6 h-6 text-neon-purple" />
  },
  {
    title: "In-memory Persistence",
    description: "Lightning fast operation simulating database storage using dictionaries for rooms, players, and transactions.",
    icon: <Database className="w-6 h-6 text-neon-cyan" />
  },
  {
    title: "Deep-linking Lobby",
    description: "Create rooms with custom balances and invite players instantly using generated deep links.",
    icon: <LinkIcon className="w-6 h-6 text-neon-purple" />
  },
  {
    title: "Dynamic Status Board",
    description: "Global Game Status panels are pinned in private chats and dynamically updated in real-time as transactions happen.",
    icon: <LayoutDashboard className="w-6 h-6 text-neon-cyan" />
  },
  {
    title: "Full Transaction Flow",
    description: "Supports Bank purchases, rent payments, Chance cards, and automatic bankruptcy handling.",
    icon: <CreditCard className="w-6 h-6 text-neon-purple" />
  }
];

export default function App() {
  return (
    <div className="min-h-screen bg-dark-bg text-white font-sans selection:bg-neon-cyan/30">
      {/* Background Grid */}
      <div className="fixed inset-0 z-0 bg-grid-pattern opacity-30 pointer-events-none"></div>
      
      {/* Header */}
      <nav className="relative z-10 max-w-7xl mx-auto px-6 py-6 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <Gamepad2 className="w-8 h-8 text-neon-cyan" />
          <span className="font-bold tracking-widest text-xl uppercase hidden sm:block">Bankir Bot</span>
        </div>
        <a 
          href="https://github.com/PiterPentester/bankirBot"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 px-4 py-2 rounded-md bg-dark-surface border border-dark-border hover:border-neon-cyan transition-colors duration-300"
        >
          <Github className="w-5 h-5" />
          <span className="font-medium text-sm uppercase tracking-widest">GitHub</span>
        </a>
      </nav>

      <main className="relative z-10 max-w-7xl mx-auto px-6 pt-20 pb-32">
        {/* Hero Section */}
        <section className="flex flex-col items-center text-center mb-32">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-dark-surface border border-dark-border mb-8"
          >
            <span className="w-2 h-2 rounded-full bg-neon-cyan animate-pulse"></span>
            <span className="text-xs font-mono text-gray-400 uppercase tracking-widest">System Online</span>
          </motion.div>
          
          <motion.h1 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.1 }}
            className="text-6xl md:text-8xl font-bold tracking-tighter mb-6"
          >
            BANKIR <span className="text-transparent bg-clip-text bg-gradient-to-r from-neon-cyan to-neon-purple">BOT</span>
          </motion.h1>
          
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="text-lg md:text-xl text-gray-400 max-w-2xl mb-10 font-light"
          >
            A Python-based Telegram Digital Banker for physical Monopoly board games. Handles virtual rooms, balances, and all transactions transparently.
          </motion.p>
          
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="flex flex-col sm:flex-row gap-4"
          >
            <a 
              href="https://github.com/PiterPentester/bankirBot"
              target="_blank"
              rel="noopener noreferrer"
              className="px-8 py-4 rounded bg-white text-black font-bold uppercase tracking-widest hover:bg-neon-cyan transition-colors duration-300 glow-cyan flex items-center justify-center gap-2"
            >
              <Github className="w-5 h-5" />
              View Source
            </a>
            <a 
              href="#getting-started"
              className="px-8 py-4 rounded bg-dark-surface border border-dark-border text-white font-bold uppercase tracking-widest hover:border-neon-purple transition-colors duration-300 flex items-center justify-center gap-2"
            >
              <Terminal className="w-5 h-5" />
              Quick Start
            </a>
          </motion.div>
        </section>

        {/* Features Grid */}
        <section className="mb-32">
          <div className="flex items-center gap-4 mb-12">
            <h2 className="text-3xl font-bold tracking-tight uppercase">Core Features</h2>
            <div className="h-[1px] flex-1 bg-gradient-to-r from-dark-border to-transparent"></div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="p-6 rounded-xl bg-dark-surface border border-dark-border hover:border-neon-cyan/50 transition-colors duration-300 group"
              >
                <div className="w-12 h-12 rounded bg-dark-bg border border-dark-border flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                  {feature.icon}
                </div>
                <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </section>

        {/* Getting Started */}
        <section id="getting-started" className="mb-20">
          <div className="flex items-center gap-4 mb-12">
            <h2 className="text-3xl font-bold tracking-tight uppercase">Deployment</h2>
            <div className="h-[1px] flex-1 bg-gradient-to-r from-dark-border to-transparent"></div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <motion.div 
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="p-8 rounded-xl bg-dark-surface border border-dark-border"
            >
              <h3 className="text-xl font-bold mb-6 flex items-center gap-3">
                <Terminal className="w-5 h-5 text-neon-cyan" />
                Installation
              </h3>
              <div className="space-y-4">
                <div className="bg-dark-bg p-4 rounded border border-dark-border font-mono text-sm overflow-x-auto">
                  <p className="text-gray-500 mb-1"># Clone the repository</p>
                  <p className="text-neon-cyan">git clone https://github.com/PiterPentester/bankirBot.git</p>
                  <p className="text-neon-cyan">cd bankirBot</p>
                  <br />
                  <p className="text-gray-500 mb-1"># Install dependencies (uses uv)</p>
                  <p className="text-neon-cyan">uv sync</p>
                  <br />
                  <p className="text-gray-500 mb-1"># Run unit tests</p>
                  <p className="text-neon-cyan">uv run pytest</p>
                </div>
              </div>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="p-8 rounded-xl bg-dark-surface border border-dark-border"
            >
              <h3 className="text-xl font-bold mb-6 flex items-center gap-3">
                <Server className="w-5 h-5 text-neon-purple" />
                Run the Bot
              </h3>
              <div className="space-y-4">
                <div className="bg-dark-bg p-4 rounded border border-dark-border font-mono text-sm overflow-x-auto">
                  <p className="text-gray-500 mb-1"># Export your Telegram token</p>
                  <p className="text-neon-purple">export BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"</p>
                  <br />
                  <p className="text-gray-500 mb-1"># Start polling</p>
                  <p className="text-neon-purple">uv run python bot.py</p>
                  <br />
                  <p className="text-gray-500 mb-1"># Or as a one-liner</p>
                  <p className="text-neon-purple">BOT_TOKEN="YOUR_TOKEN" uv run python bot.py</p>
                </div>
              </div>
            </motion.div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-dark-border bg-dark-surface py-12">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <Gamepad2 className="w-5 h-5 text-neon-cyan" />
            <span className="font-bold tracking-widest text-sm">BANKIR BOT</span>
          </div>
          <p className="text-gray-500 text-sm font-mono">
            Developed by <a href="https://github.com/PiterPentester" target="_blank" rel="noopener noreferrer" className="text-neon-cyan hover:underline">PiterPentester</a>
          </p>
          <div className="flex items-center gap-4">
            <a href="https://github.com/PiterPentester/bankirBot" target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-white transition-colors">
              <Github className="w-5 h-5" />
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
