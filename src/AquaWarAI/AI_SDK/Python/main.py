import sys

if __name__ == "__main__":
    language = sys.argv[1]
    model = sys.argv[2]
    stage = int(sys.argv[3])
    order = int(sys.argv[4])
    save_dir = sys.argv[5]
    
    if language == 'en':
        from AI_En import Agent
        myAI = Agent(model, stage, order, save_dir)
    else:
        from AI_Cn import Agent
        myAI = Agent(model, stage, order, save_dir)
    
    myAI.run()
