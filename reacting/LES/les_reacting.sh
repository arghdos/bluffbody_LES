#!/bin/bash
#SBATCH --partition=parallel	     # run on parallel partition
#SBATCH --time=6:00:00               # Job should run for no more than 12 hours
#SBATCH --nodes=2                    # two nodes
#SBATCH --ntasks=48                  # 48 cores
#SBATCH --exclude=cn[01-136,325-328] # only run on haswell
#SBATCH --mem 100G                   # up to 100 gigs
#SBATCH -o les_reacting.out
#SBATCH -e les_reacting.out
#SBATCH --mail-type=END              # mail
#SBATCH --mail-user=nicholas.curtis@uconn.edu
#SBATCH --dependency=singleton


# NOTE: IS IS IMPORTANT TO KEEP THE SBATCH COMAND AND THE INTERNAL TIME SPEC IN SYNC!!!
days="0"
hours="6"
minutes="0"
seconds="0"
# SIMILARLY WITH THE OUTPUT FILE
output="les_reacting.out"
# Should be at least 2, such that if we get out of sleep at the beginning of a
# timestep, we can safely take this time-step _and_ the next before ending.
SAFTEY_FACTOR="3"

# first, reset endtime
bash -c "foamDictionary -entry \"stopAt\" -set \"endTime\" system/controlDict"

default="3000" # s
c () {
    local a
    (( $# > 0 )) && a="$@" || read -r -p "calc: " a
    bc -l <<< "$a"
}

# next, set determine maximum step time
if [ ! -f $output ]
then
    echo "Output log ($output) not found!"
    echo "Using guessed time-step duration ${default}s."
    max_step=$default
else
    echo "Getting execution times."
    time_at_steps=($(tac $output | grep -m 10 'ExecutionTime = ' | awk -F' ' '{print $3}'))
    echo "${#time_at_steps[@]} execution times obtained"
    if [ ! $time_at_steps ]
    then
        echo "No time-steps found in $output.  This is normal _only_ on the first run of a solution."
        echo "Using guessed time-step duration ${default}s."
        max_step=$default
    else
        echo "Calculating step durations."
        # get the differences between execution times to get the step durations
        max_step="0"
        for (( i=0; i<${#time_at_steps[@]}; i++ )) ; do
            next_i=$(c "$i + 1")
            if [ ! "${time_at_steps[$next_i]+_}" ]
            then
                break
            fi
            echo "Time-step $i: ${time_at_steps[$i]}"
            time_per_step=$(c "${time_at_steps[$i]} - ${time_at_steps[$next_i]}")
            if (( $(echo "$time_per_step < 0" | bc -l) ))
            then
                # the simulation restarted in this time step, hence the duration
                # is simply the time value
                time_per_step=${time_at_steps[$i]}
            fi
            echo "Duration $i: ${time_per_step}"
            if (( $(echo "$time_per_step > $max_step" | bc -l) ))
            then
                max_step=$time_per_step
            fi
        done
        # and get maximum step duration
        echo "Maximum step duration ${max_step}s."
    fi
fi

# add safety factor
time_per_step=$(c "$max_step * $SAFTEY_FACTOR")
echo "After saftey factor: ${time_per_step}s."
if (( $(echo "$time_per_step < 5" | bc -l) ))
then
    echo "Bumping up step duration to 5 seconds to allow IPM to exit gracefully."
    time_per_step="5"
fi
sleep_duration=$(c "$days * 86400 + $hours * 3600 + $minutes * 60 + $seconds - $time_per_step")
echo "Sleeping for ${sleep_duration}s."

if (( $(echo "$sleep_duration < 0" | bc -l) ))
then
    echo "Reservation too short -- can't complete a timestep."
    exit 1
fi

# spawn a new bash process that will sleep until nearly the end of the reservation, and
# then change the stopAt entry to writeNow to allow IPM to exit gracefully
# and more importantly, write timing data
bash -c "sleep $sleep_duration; foamDictionary -entry \"stopAt\" -set \"writeNow\" system/controlDict" &
export IPM_NESTED_REGIONS=1
mpirun reactingFoamIPM -parallel
