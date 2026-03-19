import { motion } from 'framer-motion';

export const Greeting = () => {
  return (
    <div
      key="overview"
      className="mx-auto mt-4 flex size-full max-w-3xl flex-col items-center justify-center px-4 md:mt-16 md:px-8"
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.8 }}
        transition={{ delay: 0.3 }}
        className="mb-8"
      >
        <img src="/Farma Bricks.png" alt="Farma Bricks" className="h-20 w-auto" />
      </motion.div>
      
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 10 }}
        transition={{ delay: 0.5 }}
        className="font-semibold text-xl md:text-2xl"
      >
        Bem-vindo ao Assistente Farma Bricks!
      </motion.div>
      
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 10 }}
        transition={{ delay: 0.6 }}
        className="text-xl text-zinc-500 md:text-2xl"
      >
        Como posso ajudár hoje?
      </motion.div>
    </div>
  );
};